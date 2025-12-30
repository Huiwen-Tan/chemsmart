"""
xTB job runner implementation.

This module contains the job runner classes for executing xTB semi-empirical
quantum chemistry calculations on different computing environments.
"""

import logging
import os
import shlex
import subprocess
from contextlib import suppress
from functools import lru_cache
from glob import glob
from shutil import copy

from chemsmart.jobs.runner import JobRunner
from chemsmart.settings.xtb import XTBExecutable

logger = logging.getLogger(__name__)


class XTBJobRunner(JobRunner):
    """
    xTB-specific job runner.

    This class handles the execution of xTB semi-empirical quantum chemistry
    calculations with support for scratch directories, file management,
    and command-line argument building.

    xTB is command-line driven and generates multiple output files in
    the working directory (xtbopt.xyz, charges, hessian, etc.).

    Attributes:
        JOBTYPES (list): Supported job types handled by this runner.
        PROGRAM (str): Program identifier ('xtb').
        FAKE (bool): Whether this runner operates in fake/test mode.
        SCRATCH (bool): Whether to use scratch directories by default.
        server: Server configuration used for execution.
        scratch (bool): Whether scratch is enabled for this runner.
        scratch_dir (str): Path to scratch directory, if used.
        num_cores (int): Number of CPU cores allocated (from server).
        num_gpus (int): Number of GPUs allocated (from server).
        mem_gb (int): Memory allocation in gigabytes (from server).
    """

    JOBTYPES = ["xtbjob", "xtbsp", "xtbopt"]

    PROGRAM = "xtb"

    FAKE = False
    SCRATCH = True

    def __init__(
        self, server, scratch=None, fake=False, scratch_dir=None, **kwargs
    ):
        """
        Initialize the xTB job runner.

        Args:
            server: Server configuration object
            scratch: Whether to use scratch directory (default: True)
            fake: Whether to use fake runner for testing
            scratch_dir: Path to scratch directory
            **kwargs: Additional keyword arguments
        """
        # Use default SCRATCH if scratch is not explicitly set
        if scratch is None:
            scratch = self.SCRATCH  # default to True for xTB jobs
        super().__init__(
            server=server,
            scratch=scratch,
            scratch_dir=scratch_dir,
            fake=fake,
            **kwargs,
        )
        logger.debug(f"Jobrunner server: {self.server}")
        logger.debug(f"Jobrunner num cores: {self.num_cores}")
        logger.debug(f"Jobrunner scratch: {self.scratch}")
        logger.debug(f"Jobrunner delete_scratch: {self.delete_scratch}")

    @property
    @lru_cache(maxsize=12)
    def executable(self):
        """
        Get the executable class object for xTB.

        Returns:
            XTBExecutable: xTB executable configuration object

        Raises:
            FileNotFoundError: If xTB executable cannot be found
        """
        try:
            logger.info(
                f"Obtaining executable from server: {self.server.name}"
            )
            executable = XTBExecutable.from_servername(
                servername=self.server.name
            )
            return executable
        except FileNotFoundError as e:
            logger.warning(
                f"No server file {self.server} is found or xTB not configured: {e}\n"
                f"Attempting auto-detection of xTB"
            )
            # Try auto-detection
            return XTBExecutable(auto_detect=True)

    def _prerun(self, job):
        """
        Perform pre-run setup for the job.

        Args:
            job: The job object to prepare for execution
        """
        self._assign_variables(job)

    def _assign_variables(self, job):
        """
        Set proper file paths for job input, output, and error files.

        Configures paths for execution in scratch directory or job directory.

        Args:
            job: The job object to configure paths for
        """
        if self.scratch and self.scratch_dir:
            self._set_up_variables_in_scratch(job)
        else:
            self._set_up_variables_in_job_directory(job)

        if self.executable and self.executable.local_run is not None:
            logger.info(f"Local run is {self.executable.local_run}.")
            job.local = self.executable.local_run

    def _set_up_variables_in_scratch(self, job):
        """
        Set up file paths for execution in scratch directory.

        Args:
            job: The job object to configure for scratch execution
        """
        scratch_job_dir = os.path.join(self.scratch_dir, job.label)
        if not os.path.exists(scratch_job_dir):
            with suppress(FileExistsError):
                os.makedirs(scratch_job_dir)
        self.running_directory = scratch_job_dir
        logger.debug(f"Running directory: {self.running_directory}")

        job_inputfile = job.label + ".xyz"
        scratch_job_inputfile = os.path.join(scratch_job_dir, job_inputfile)
        self.job_inputfile = os.path.abspath(scratch_job_inputfile)

        job_errfile = job.label + ".err"
        scratch_job_errfile = os.path.join(scratch_job_dir, job_errfile)
        self.job_errfile = os.path.abspath(scratch_job_errfile)

        job_outputfile = job.label + ".out"
        scratch_job_outputfile = os.path.join(scratch_job_dir, job_outputfile)
        self.job_outputfile = os.path.abspath(scratch_job_outputfile)

    def _set_up_variables_in_job_directory(self, job):
        """
        Set up file paths for execution in job directory.

        Args:
            job: The job object to configure for job directory execution
        """
        self.running_directory = job.folder
        logger.debug(f"Running directory: {self.running_directory}")
        self.job_inputfile = os.path.abspath(job.inputfile)
        self.job_errfile = os.path.abspath(job.errfile)
        self.job_outputfile = os.path.abspath(job.outputfile)

    def _write_input(self, job):
        """
        Write the input file for the job.

        Args:
            job: The job object to write input for
        """
        from chemsmart.jobs.xtb.writer import XTBInputWriter

        input_writer = XTBInputWriter(job=job)
        input_writer.write(target_directory=self.running_directory)

    def _get_command(self, job):
        """
        Get the command string to execute the xTB job.

        xTB is command-line driven, so we build the command from
        settings rather than reading an input file.

        Args:
            job: The job object to get command for

        Returns:
            str: Command string for job execution
        """
        exe = self._get_executable()

        # Start with executable and input file
        command_parts = [exe, self.job_inputfile]

        # Add command-line arguments from settings
        args = job.settings.get_command_args()
        command_parts.extend(args)

        # Join into command string
        command = " ".join(command_parts)
        return command

    def _create_process(self, job, command, env):
        """
        Create subprocess for job execution.

        Args:
            job: The job object to execute
            command: Command string to execute
            env: Environment variables for execution

        Returns:
            subprocess.Popen: Process object for the running job
        """
        with (
            open(self.job_outputfile, "w") as out,
            open(self.job_errfile, "w") as err,
        ):
            logger.info(
                f"Command executed: {command}\n"
                f"Writing output file to: {self.job_outputfile}\n"
                f"And err file to: {self.job_errfile}"
            )
            logger.debug(f"Environments for running: {self.executable.env}")
            return subprocess.Popen(
                shlex.split(command),
                stdout=out,
                stderr=err,
                env=env,
                cwd=self.running_directory,
            )

    def _get_executable(self):
        """
        Get executable path for xTB.

        Returns:
            str: Path to xTB executable
        """
        exe = self.executable.get_executable()
        logger.info(f"xTB executable: {exe}")
        return exe

    def _postrun(self, job):
        """
        Perform post-run cleanup and file management.

        xTB generates multiple files in the working directory.
        Copy all relevant files back to the job folder.

        Args:
            job: The completed job object
        """
        logger.debug(f"Scratch: {self.scratch}")

        if self.scratch:
            logger.debug(f"Running directory: {self.running_directory}")
            # Copy all xTB output files to job folder
            # xTB generates: xtbopt.xyz, charges, wbo, xtbrestart, hessian, etc.
            for file in glob(f"{self.running_directory}/*"):
                filename = os.path.basename(file)
                # Skip temporary and restart files
                if not filename.endswith(
                    (".tmp", ".tmp.*", "xtbrestart", ".xtboptok")
                ):
                    logger.info(
                        f"Copying file {file} from {self.running_directory} "
                        f"to {job.folder}"
                    )
                    try:
                        copy(file, job.folder)
                    except Exception as e:
                        logger.error(
                            f"Failed to copy file {file} to {job.folder}: {e}"
                        )


class FakeXTBJobRunner(XTBJobRunner):
    """
    Fake xTB job runner for testing purposes.

    This class simulates xTB job execution without actually running
    calculations, useful for testing and development.

    Attributes:
        PROGRAM (str): Program identifier ('xtb').
        JOBTYPES (list): Supported job types handled (inherits from XTBJobRunner).
        FAKE (bool): True for this runner to indicate fake mode.
        SCRATCH (bool): Whether to use scratch directories (inherits default).
        server: Server configuration used for execution.
        scratch (bool): Whether scratch is enabled for this runner.
        scratch_dir (str): Path to scratch directory, if used.
        num_cores (int): Number of CPU cores allocated (from server).
        num_gpus (int): Number of GPUs allocated (from server).
        mem_gb (int): Memory allocation in gigabytes (from server).
    """

    FAKE = True

    def __init__(self, server, scratch=None, fake=True, **kwargs):
        """
        Initialize the fake xTB job runner.

        Args:
            server: Server configuration object
            scratch: Whether to use scratch directory
            fake: Always True for fake runner
            **kwargs: Additional keyword arguments
        """
        super().__init__(server=server, scratch=scratch, fake=fake, **kwargs)

    def run(self, job):
        """
        Run a fake xTB job.

        Args:
            job: The job object to run

        Returns:
            int: Return code from fake execution
        """
        self._prerun(job=job)
        self._write_input(job=job)
        returncode = FakeXTB(self.job_inputfile, job.settings).run(
            self.job_outputfile
        )
        self._postrun(job=job)
        self._postrun_cleanup(job=job)
        return returncode


class FakeXTB:
    """
    Fake xTB execution simulator.

    This class simulates xTB program execution by generating
    fake output files for testing purposes.

    Attributes:
        input_file (str): Path to the input XYZ file.
        settings (XTBJobSettings): Job settings for the simulation.
    """

    def __init__(self, input_file, settings):
        """
        Initialize the fake xTB simulator.

        Args:
            input_file: Path to the input XYZ file
            settings: XTB job settings
        """
        self.input_file = input_file
        self.settings = settings

    def run(self, output_file):
        """
        Run the fake xTB calculation.

        Generates a fake output file with standard xTB output format
        for testing purposes.

        Args:
            output_file: Path to write the fake output file

        Returns:
            int: Return code (always 0 for successful fake run)
        """
        # Read input coordinates
        with open(self.input_file) as f:
            lines = f.readlines()

        num_atoms = int(lines[0].strip())

        # Write fake output
        with open(output_file, "w") as g:
            g.write("      -----------------------------------------------------------\n")
            g.write("     |                   =====================                   |\n")
            g.write("     |                           x T B                           |\n")
            g.write("     |                   =====================                   |\n")
            g.write("     |                         S. Grimme                         |\n")
            g.write("     |          Mulliken Center for Theoretical Chemistry        |\n")
            g.write("     |                    University of Bonn                     |\n")
            g.write("      -----------------------------------------------------------\n")
            g.write("\n")
            g.write(f"   * xtb version 6.6.1 (fake)\n")
            g.write("\n")
            g.write(f"      # atoms: {num_atoms}\n")
            g.write(f"     charge: {self.settings.charge}\n")
            g.write(f"     unpaired: {self.settings.multiplicity - 1}\n")
            g.write(f"     method: {self.settings.method}\n")
            g.write("\n")

            if self.settings.job_type == "opt":
                g.write("   *** GEOMETRY OPTIMIZATION ***\n")
                g.write("   optimization converged!\n")
                g.write("\n")

            g.write("         -------------------------------------------------\n")
            g.write("         |                Property Printout                |\n")
            g.write("         -------------------------------------------------\n")
            g.write("\n")
            g.write("         * total energy  :      -12.34567890 Eh\n")
            g.write("\n")
            g.write("         -------------------------------------------------\n")
            g.write("         |                   Mulliken Charges              |\n")
            g.write("         -------------------------------------------------\n")
            for i in range(num_atoms):
                g.write(f"         {i+1}  C    -0.123456\n")
            g.write("\n")
            g.write("   * finished run on 2024/01/01 at 12:00:00.000\n")
            g.write("\n")
            g.write("   * wall-time:     0 d,  0 h,  0 min,  0.123 sec\n")
            g.write("   *  cpu-time:     0 d,  0 h,  0 min,  0.123 sec\n")

        # If optimization, create fake xtbopt.xyz
        if self.settings.job_type == "opt":
            output_dir = os.path.dirname(output_file)
            xtbopt_file = os.path.join(output_dir, "xtbopt.xyz")
            with open(xtbopt_file, "w") as g:
                g.write(f"{num_atoms}\n")
                g.write("optimized geometry\n")
                # Copy coordinates from input (in real case would be optimized)
                for line in lines[2 : 2 + num_atoms]:
                    g.write(line)

        return 0
