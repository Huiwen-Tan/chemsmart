"""
xTB job runner implementation.

This module contains the job runner classes for executing xTB semi-empirical
quantum chemistry calculations on different computing environments.
"""

import logging
import os
import subprocess
from contextlib import suppress
from functools import lru_cache

import ase.io

from chemsmart.jobs.runner import JobRunner
from chemsmart.settings.executable import XTBExecutable

logger = logging.getLogger(__name__)


class XTBJobRunner(JobRunner):
    """
    xTB-specific job runner.

    This class handles the execution of xTB semi-empirical quantum chemistry
    calculations with support for directory-based execution and various job types.

    Attributes:
        JOBTYPES (list): Supported job types handled by this runner.
        PROGRAM (str): Program identifier ('xtb').
        FAKE (bool): Whether this runner operates in fake/test mode.
        SCRATCH (bool): Whether to use scratch directories by default.
    """

    JOBTYPES = [
        "xtbsp",
        "xtbopt",
    ]

    PROGRAM = "xtb"

    FAKE = False
    SCRATCH = False  # xTB can run in place by default

    def __init__(
        self, server, scratch=None, fake=False, scratch_dir=None, **kwargs
    ):
        """
        Initialize the xTB job runner.

        Args:
            server: Server configuration object
            scratch: Whether to use scratch directory
            fake: Whether to use fake runner for testing
            scratch_dir: Path to scratch directory
            **kwargs: Additional keyword arguments
        """
        # Use default SCRATCH if scratch is not explicitly set
        if scratch is None:
            scratch = self.SCRATCH
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

    @property
    @lru_cache(maxsize=12)
    def executable(self):
        """
        Get the executable class object for xTB.

        Returns:
            XTBExecutable: xTB executable configuration object

        Raises:
            FileNotFoundError: If server configuration file is not found
        """
        try:
            logger.info(
                f"Obtaining executable from server: {self.server.name}"
            )
            executable = XTBExecutable.from_servername(
                servername=self.server.name
            )
            return executable
        except (FileNotFoundError, KeyError) as e:
            logger.warning(
                f"No server file or XTB config found for {self.server}: {e}\n"
                f"Attempting auto-detection of xTB executable"
            )
            # Try to create executable with auto-detection
            return XTBExecutable(executable_folder=None)

    def _prerun(self, job):
        """
        Perform pre-run setup for the job.

        Args:
            job: The job object to prepare for execution
        """
        self._assign_variables(job)
        self._write_input(job)

    def _assign_variables(self, job):
        """
        Set proper file paths and directory for job execution.

        Args:
            job: The job object to configure paths for
        """
        if self.scratch and self.scratch_dir:
            self._set_up_variables_in_scratch(job)
        else:
            # Run in job folder
            self.running_directory = job.folder
            self.running_inputfile = job.inputfile
            self.running_outputfile = job.outputfile
            self.running_errfile = job.errfile

    def _set_up_variables_in_scratch(self, job):
        """
        Set up execution directory and file paths in scratch.

        Args:
            job: The job object to configure for scratch execution
        """
        # Create job-specific scratch directory
        job_scratch_dir = os.path.join(self.scratch_dir, job.label)
        with suppress(FileExistsError):
            os.makedirs(job_scratch_dir, exist_ok=True)
            logger.info(f"Created scratch folder: {job_scratch_dir}")

        self.running_directory = job_scratch_dir
        self.running_inputfile = os.path.join(job_scratch_dir, f"{job.label}.xyz")
        self.running_outputfile = os.path.join(job_scratch_dir, f"{job.label}.out")
        self.running_errfile = os.path.join(job_scratch_dir, f"{job.label}.err")

    def _write_input(self, job):
        """
        Write the input geometry file for xTB.

        xTB uses xyz format for molecular geometry input.

        Args:
            job: The job object containing molecule and settings
        """
        # Write xyz file using ASE
        molecule_ase = job.molecule.to_ase()
        ase.io.write(self.running_inputfile, molecule_ase, format="xyz")
        logger.info(f"Wrote input file: {self.running_inputfile}")

    def _get_command(self, job):
        """
        Build the xTB command line.

        Args:
            job: The job object to build command for

        Returns:
            list: Command and arguments for xTB execution
        """
        # Get xTB executable path
        executable_path = self.executable.get_executable()
        if executable_path is None:
            raise RuntimeError(
                "xTB executable not found. Please ensure xTB is installed "
                "and in PATH, or configure EXEFOLDER in server settings."
            )

        # Build command arguments based on settings
        input_filename = os.path.basename(self.running_inputfile)
        command_args = job.settings.build_command_args(input_filename)

        # Full command
        command = [executable_path] + command_args

        logger.info(f"xTB command: {' '.join(command)}")
        return command

    def _create_process(self, job, command, env):
        """
        Create subprocess for xTB execution.

        Args:
            job: The job object
            command: Command list to execute
            env: Environment variables

        Returns:
            subprocess.Popen: Process object for xTB execution
        """
        # xTB must run in its execution directory to generate output files correctly
        logger.info(f"Running xTB in directory: {self.running_directory}")

        # Set OMP_NUM_THREADS if parallel is specified
        if job.settings.parallel:
            env["OMP_NUM_THREADS"] = str(job.settings.parallel)
        elif self.num_cores:
            env["OMP_NUM_THREADS"] = str(self.num_cores)

        # Open output and error files using context managers is better,
        # but subprocess.Popen needs file objects that stay open
        # We'll ensure they're closed in _run() after process completes
        try:
            outfile = open(self.running_outputfile, "w")
            errfile = open(self.running_errfile, "w")

            process = subprocess.Popen(
                command,
                stdout=outfile,
                stderr=errfile,
                cwd=self.running_directory,
                env=env,
            )

            # Store file handles to close later in _run()
            process._outfile = outfile
            process._errfile = errfile

            return process
        except Exception as e:
            # Clean up file handles if process creation fails
            if 'outfile' in locals():
                outfile.close()
            if 'errfile' in locals():
                errfile.close()
            raise

    def _run(self, process, **kwargs):
        """
        Run the xTB process and wait for completion.

        Args:
            process: The subprocess.Popen object
            **kwargs: Additional keyword arguments

        Returns:
            int: Return code of the process
        """
        returncode = process.wait()

        # Close file handles
        if hasattr(process, "_outfile"):
            process._outfile.close()
        if hasattr(process, "_errfile"):
            process._errfile.close()

        return returncode

    def _postrun(self, job, **kwargs):
        """
        Perform post-run tasks.

        Copy output files from scratch to job folder if scratch was used.

        Args:
            job: The job object
            **kwargs: Additional keyword arguments
        """
        if self.scratch and self.scratch_dir:
            self._copy_files_from_scratch_to_job_folder(job)

    def _copy_files_from_scratch_to_job_folder(self, job):
        """
        Copy output files from scratch directory back to job folder.

        Args:
            job: The job object
        """
        import shutil
        from pathlib import Path

        # Validate that job folder exists and is a directory
        job_folder_path = Path(job.folder).resolve()
        if not job_folder_path.is_dir():
            logger.error(f"Job folder does not exist: {job_folder_path}")
            return

        # Define files to copy
        files_to_copy = [
            (self.running_outputfile, job.outputfile),
            (self.running_errfile, job.errfile),
        ]

        # Also copy common xTB output files
        common_outputs = [
            "xtbopt.xyz",  # Optimized geometry
            "xtbopt.log",  # Optimization log
            "xtb.out",     # Additional output
            "charges",     # Charges file
            "wbo",         # Wiberg bond orders
            "gfnff_topo",  # GFN-FF topology
            "xtbrestart",  # Restart file
            "xtbtopo.mol", # Topology
            "hessian",     # Hessian matrix
        ]

        for filename in common_outputs:
            src = os.path.join(self.running_directory, filename)
            dst = os.path.join(job.folder, filename)
            if os.path.exists(src):
                files_to_copy.append((src, dst))

        # Copy files with path validation
        for src, dst in files_to_copy:
            if os.path.exists(src):
                try:
                    # Validate destination is within job folder
                    dst_path = Path(dst).resolve()
                    if not dst_path.is_relative_to(job_folder_path):
                        logger.error(
                            f"Destination {dst} is outside job folder, skipping"
                        )
                        continue

                    shutil.copy2(src, dst)
                    logger.debug(f"Copied {src} to {dst}")
                except Exception as e:
                    logger.warning(f"Failed to copy {src} to {dst}: {e}")
