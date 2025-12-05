"""
Scheduler for parallel job submission via scheduler arrays.

This module provides abstract and concrete scheduler classes for managing
parallel submission of computational chemistry jobs using array functionality
across different scheduler systems (SLURM, PBS, LSF).
"""

import logging
import shlex
import subprocess
from abc import ABC, ABCMeta, abstractmethod
from typing import List, Optional

from chemsmart.settings.user import ChemsmartUserSettings
from chemsmart.utils.mixins import RegistryMeta

user_settings = ChemsmartUserSettings()

logger = logging.getLogger(__name__)


class ABCRegistryMeta(ABCMeta, RegistryMeta):
    """Combined metaclass for ABC and RegistryMixin functionality."""

    pass


class ArrayScheduler(ABC, metaclass=ABCRegistryMeta):
    """
    Abstract base class for array job schedulers.

    Provides the foundation for scheduler-specific array job implementations
    that handle the creation and submission of parallel computational chemistry
    jobs to various cluster management systems.

    Subclasses must implement:
        - _write_scheduler_options(): Write scheduler-specific directives
        - _write_change_to_job_directory(): Write directory change command
        - _get_submit_command(): Get the submission command
        - _parse_job_id(): Parse job ID from submission output
        - array_task_id_var: Property returning the array task ID variable name

    Attributes:
        NAME (str): Class-level identifier for the scheduler type.
        jobs (list): List of jobs to be scheduled.
        max_parallel (int): Maximum concurrent array tasks (nodes).
        server: Server configuration for submission.
        job_name (str): Base name for the array job.
    """

    NAME: Optional[str] = None
    # Flag to control whether this class should be registered in the registry
    REGISTERABLE = True

    # Registry for subclass tracking
    _REGISTRY: List = []

    def __init_subclass__(cls, **kwargs):
        """
        Automatically register subclass in the registry.

        Called when a subclass is created to automatically add it
        to the shared registry if REGISTERABLE is True.
        """
        super().__init_subclass__(**kwargs)
        if cls.REGISTERABLE:
            cls._REGISTRY.append(cls)

    @classmethod
    def subclasses(cls, allow_abstract: bool = False) -> List:
        """
        Get all registered subclasses of this class.

        Args:
            allow_abstract: Whether to include abstract classes.

        Returns:
            List of subclass types.
        """
        import inspect

        return [
            c
            for c in cls._REGISTRY
            if issubclass(c, cls)
            and c != cls
            and (not inspect.isabstract(c) or allow_abstract)
        ]

    def __init__(
        self,
        jobs: List,
        server,
        max_parallel: Optional[int] = None,
        job_name: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize the array scheduler.

        Args:
            jobs: List of jobs to be scheduled.
            server: Server configuration with scheduler settings.
            max_parallel: Maximum concurrent array tasks (nodes).
            job_name: Base name for the array job.
            **kwargs: Additional keyword arguments.
        """
        self.jobs = jobs
        self.max_parallel = max_parallel
        self.server = server
        self.job_name = job_name
        self.kwargs = kwargs

    @property
    def num_jobs(self) -> int:
        """Get the number of jobs to be scheduled."""
        return len(self.jobs)

    @property
    def job_labels(self) -> List[str]:
        """Get the labels for all jobs in the array."""
        return [job.label for job in self.jobs]

    @property
    @abstractmethod
    def array_spec(self) -> str:
        """
        Get the scheduler-specific array specification string.

        Returns:
            str: Array specification string for the scheduler.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def array_task_id_var(self) -> str:
        """
        Get the environment variable name for array task ID.

        Returns:
            str: Name of the environment variable (e.g., SLURM_ARRAY_TASK_ID).
        """
        raise NotImplementedError

    def _write_bash_header(self, f):
        """
        Write the bash shebang header to the script.

        Args:
            f: File handle for writing the script.
        """
        f.write("#!/bin/bash\n\n")

    @abstractmethod
    def _write_scheduler_options(self, f):
        """
        Write scheduler-specific directives to the submission script.

        This method must be implemented by subclasses to provide
        scheduler-specific directives and resource requests.

        Args:
            f: File handle for writing scheduler directives.
        """
        raise NotImplementedError

    @abstractmethod
    def _write_change_to_job_directory(self, f):
        """
        Write scheduler-specific directory change command.

        Each scheduler system has different environment variables
        for the job submission directory.

        Args:
            f: File handle for writing directory change command.
        """
        raise NotImplementedError

    def _write_job_array_mapping(self, f):
        """
        Write the job labels array mapping.

        Args:
            f: File handle for writing job mapping.
        """
        f.write("# Job labels array\n")
        f.write("JOBS=(\n")
        for label in self.job_labels:
            f.write(f'    "{label}"\n')
        f.write(")\n\n")

    def _write_job_selection(self, f):
        """
        Write commands to select current job from array.

        Args:
            f: File handle for writing job selection logic.
        """
        f.write("# Get current job label\n")
        f.write(f"JOB_LABEL=${{JOBS[${self.array_task_id_var}]}}\n")
        f.write(
            f'echo "Running job: $JOB_LABEL (array task ${self.array_task_id_var})"\n\n'
        )

    def _write_job_execution(self, f):
        """
        Write commands to execute the selected job.

        Args:
            f: File handle for writing job execution commands.
        """
        f.write("# Execute the job\n")
        f.write('if [ -f "chemsmart_run_${JOB_LABEL}.py" ]; then\n')
        f.write("    chmod +x chemsmart_run_${JOB_LABEL}.py\n")
        f.write("    python chemsmart_run_${JOB_LABEL}.py\n")
        f.write("else\n")
        f.write('    echo "Error: Run script not found for job $JOB_LABEL"\n')
        f.write("    exit 1\n")
        f.write("fi\n\n")
        f.write("wait\n")

    def _write_script(self):
        """
        Write the complete array submission script.
        """
        with open(self.submit_script, "w") as f:
            logger.debug(f"Written array script to: {self.submit_script}")
            self._write_bash_header(f)
            self._write_scheduler_options(f)
            self._write_change_to_job_directory(f)
            self._write_job_array_mapping(f)
            self._write_job_selection(f)
            self._write_job_execution(f)

    @property
    def submit_script(self) -> str:
        """Get the filename for the submission script."""
        if self.job_name is not None:
            return f"chemsmart_array_sub_{self.job_name}.sh"
        return "chemsmart_array_sub.sh"

    @abstractmethod
    def _get_submit_command(self) -> str:
        """
        Get the command to submit the job.

        Returns:
            str: The submission command (e.g., 'sbatch script.sh').
        """
        raise NotImplementedError

    @abstractmethod
    def _parse_job_id(self, output: str) -> Optional[str]:
        """
        Parse the job ID from submission output.

        Args:
            output: Output from the submission command.

        Returns:
            Optional[str]: The job ID if found, None otherwise.
        """
        raise NotImplementedError

    def submit(self, test: bool = False) -> Optional[str]:
        """
        Submit the array job.

        Args:
            test: If True, only write script without submitting.

        Returns:
            Optional[str]: Job ID if submitted, None if test mode or no jobs.

        Raises:
            ValueError: If there are no jobs to submit.
        """
        # Validate that we have jobs to submit
        if self.num_jobs == 0:
            logger.warning("No jobs to submit - empty job list")
            raise ValueError(f"Cannot submit {self.NAME} array with no jobs")

        # Write the submission script
        self._write_script()

        if test:
            logger.info(
                f"Test mode: script written to {self.submit_script}, "
                "not submitted."
            )
            return None

        # Submit using scheduler-specific command
        command = self._get_submit_command()
        logger.info(f"Submitting {self.NAME} array job: {command}")

        try:
            result = subprocess.run(
                shlex.split(command),
                capture_output=True,
                text=True,
                check=True,
            )

            output = result.stdout.strip()
            logger.info(f"{self.NAME} submission output: {output}")

            job_id = self._parse_job_id(output)
            if job_id:
                logger.info(
                    f"Submitted {self.NAME} array job with ID: {job_id}"
                )
                return job_id

            return output

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to submit {self.NAME} array job: {e.stderr}")
            raise RuntimeError(
                f"{self.NAME} submission failed: {e.stderr}"
            ) from e

    @classmethod
    def from_scheduler_type(cls, scheduler_type: str, **kwargs):
        """
        Create an array scheduler instance for the specified scheduler type.

        Factory method that finds and instantiates the appropriate
        scheduler subclass based on the scheduler type name.

        Args:
            scheduler_type: Name of the scheduler system
                (e.g., "PBS", "SLURM", "LSF").
            **kwargs: Additional arguments passed to the scheduler constructor.

        Returns:
            ArrayScheduler: Instance of the appropriate scheduler subclass.

        Raises:
            ValueError: If no scheduler is found for the specified type.
        """
        schedulers = cls.subclasses()
        for scheduler in schedulers:
            if scheduler.NAME == scheduler_type:
                return scheduler(**kwargs)
        available = [s.NAME for s in schedulers if s.NAME]
        raise ValueError(
            f"Could not find array scheduler for type: {scheduler_type}. "
            f"Available: {available}"
        )

    def render_script(self) -> str:
        """
        Render the complete submission script as a string.

        Returns:
            str: The complete submission script content.
        """
        import io

        buffer = io.StringIO()
        self._write_bash_header(buffer)
        self._write_scheduler_options(buffer)
        self._write_change_to_job_directory(buffer)
        self._write_job_array_mapping(buffer)
        self._write_job_selection(buffer)
        self._write_job_execution(buffer)
        return buffer.getvalue()

    def write_script(self, directory: Optional[str] = None) -> str:
        """
        Write the submission script to a file.

        Args:
            directory: Directory to write the script. Defaults to current dir.

        Returns:
            str: Path to the written script file.
        """
        import os

        if directory is None:
            script_path = self.submit_script
        else:
            script_path = os.path.join(directory, self.submit_script)

        with open(script_path, "w") as f:
            f.write(self.render_script())

        logger.info(f"Written {self.NAME} array script to: {script_path}")
        return script_path


class SLURMArrayScheduler(ArrayScheduler):
    """
    SLURM array job scheduler.

    Implements parallel job submission using SLURM array functionality.
    Each array task runs a single job. When a node finishes, the next
    job in the queue is automatically assigned to it.

    Attributes:
        NAME (str): Identifier for SLURM scheduler type ('SLURM').
    """

    NAME = "SLURM"

    @property
    def array_spec(self) -> str:
        """
        Get the SLURM array specification string.

        Returns:
            str: Array spec like '0-99%4' for 100 jobs with max 4 concurrent.
                Returns empty string if no jobs.
        """
        if self.num_jobs == 0:
            return ""
        if self.num_jobs == 1:
            return "0-0"
        # SLURM arrays are 0-indexed
        array_range = f"0-{self.num_jobs - 1}"
        if self.max_parallel and self.max_parallel < self.num_jobs:
            array_range += f"%{self.max_parallel}"
        return array_range

    @property
    def array_task_id_var(self) -> str:
        """Get SLURM array task ID variable name."""
        return "SLURM_ARRAY_TASK_ID"

    def _write_scheduler_options(self, f):
        """
        Write SLURM-specific directives to the submission script.

        Args:
            f: File handle for writing SLURM directives.
        """
        f.write(f"#SBATCH --job-name={self.job_name}\n")
        f.write(f"#SBATCH --array={self.array_spec}\n")
        f.write(f"#SBATCH --output={self.job_name}_%A_%a.slurmout\n")
        f.write(f"#SBATCH --error={self.job_name}_%A_%a.slurmerr\n")
        if self.server.num_gpus:
            f.write(f"#SBATCH --gres=gpu:{self.server.num_gpus}\n")
        f.write(
            f"#SBATCH --nodes=1 --ntasks-per-node={self.server.num_cores} "
            f"--mem={self.server.mem_gb}G\n"
        )
        if self.server.queue_name:
            f.write(f"#SBATCH --partition={self.server.queue_name}\n")
        if self.server.num_hours:
            f.write(f"#SBATCH --time={self.server.num_hours}:00:00\n")
        if user_settings is not None:
            if user_settings.data.get("PROJECT"):
                f.write(f"#SBATCH --account={user_settings.data['PROJECT']}\n")
            if user_settings.data.get("EMAIL"):
                f.write(f"#SBATCH --mail-user={user_settings.data['EMAIL']}\n")
                f.write("#SBATCH --mail-type=END,FAIL\n")
        f.write("\n")
        f.write("\n")

    def _write_change_to_job_directory(self, f):
        """
        Write SLURM-specific directory change command.

        Args:
            f: File handle for writing directory change command.
        """
        f.write("cd $SLURM_SUBMIT_DIR\n\n")

    def _get_submit_command(self) -> str:
        """Get SLURM submission command."""
        return f"sbatch {self.submit_script}"

    def _parse_job_id(self, output: str) -> Optional[str]:
        """Parse job ID from SLURM sbatch output."""
        if "Submitted batch job" in output:
            return output.split()[-1]
        return None


class PBSArrayScheduler(ArrayScheduler):
    """
    PBS array job scheduler.

    Implements parallel job submission using PBS array functionality.
    Each array task runs a single job.

    Attributes:
        NAME (str): Identifier for PBS scheduler type ('PBS').
    """

    NAME = "PBS"

    @property
    def array_spec(self) -> str:
        """
        Get the PBS array specification string.

        Returns:
            str: Array spec like '0-99%4' for 100 jobs with max 4 concurrent.
                Returns empty string if no jobs.
        """
        if self.num_jobs == 0:
            return ""
        if self.num_jobs == 1:
            return "0"
        # PBS arrays are 0-indexed
        array_range = f"0-{self.num_jobs - 1}"
        if self.max_parallel and self.max_parallel < self.num_jobs:
            array_range += f"%{self.max_parallel}"
        return array_range

    @property
    def array_task_id_var(self) -> str:
        """Get PBS array task ID variable name."""
        return "PBS_ARRAY_INDEX"

    def _write_scheduler_options(self, f):
        """
        Write PBS-specific directives to the submission script.

        Args:
            f: File handle for writing PBS directives.
        """
        f.write(f"#PBS -N {self.job_name}\n")
        f.write(f"#PBS -J {self.array_spec}\n")
        f.write(f"#PBS -o {self.job_name}.pbsout\n")
        f.write(f"#PBS -e {self.job_name}.pbserr\n")
        if self.server.num_gpus > 0:
            f.write(f"#PBS -l gpus={self.server.num_gpus}\n")
        f.write(
            f"#PBS -l select=1:ncpus={self.server.num_cores}:"
            f"mpiprocs={self.server.num_cores}:mem={self.server.mem_gb}G\n"
        )
        if self.server.queue_name:
            f.write(f"#PBS -q {self.server.queue_name}\n")
        if self.server.num_hours:
            f.write(f"#PBS -l walltime={self.server.num_hours}:00:00\n")
        if user_settings is not None:
            if user_settings.data.get("PROJECT"):
                f.write(f"#PBS -P {user_settings.data['PROJECT']}\n")
            if user_settings.data.get("EMAIL"):
                f.write(f"#PBS -M {user_settings.data['EMAIL']}\n")
                f.write("#PBS -m abe\n")
        f.write("\n")
        f.write("\n")

    def _write_change_to_job_directory(self, f):
        """
        Write PBS-specific directory change command.

        Args:
            f: File handle for writing directory change command.
        """
        f.write("cd $PBS_O_WORKDIR\n\n")

    def _get_submit_command(self) -> str:
        """Get PBS submission command."""
        return f"qsub {self.submit_script}"

    def _parse_job_id(self, output: str) -> Optional[str]:
        """Parse job ID from PBS qsub output."""
        # PBS typically returns job ID directly
        if output:
            return output.split(".")[0] if "." in output else output
        return None


class LSFArrayScheduler(ArrayScheduler):
    """
    LSF (Load Sharing Facility) array job scheduler.

    Implements parallel job submission using LSF job array functionality.
    Each array task runs a single job.

    Attributes:
        NAME (str): Identifier for LSF scheduler type ('LSF').
    """

    NAME = "LSF"

    @property
    def array_spec(self) -> str:
        """
        Get the LSF array specification string.

        Returns:
            str: Array spec like '[1-100]%4' for 100 jobs with max 4 concurrent.
                Returns empty string if no jobs.
        """
        if self.num_jobs == 0:
            return ""
        if self.num_jobs == 1:
            return "[1]"
        # LSF arrays are 1-indexed
        array_range = f"[1-{self.num_jobs}]"
        if self.max_parallel and self.max_parallel < self.num_jobs:
            array_range += f"%{self.max_parallel}"
        return array_range

    @property
    def array_task_id_var(self) -> str:
        """Get LSF array task ID variable name."""
        return "LSB_JOBINDEX"

    def _write_job_selection(self, f):
        """
        Write commands to select current job from array.

        LSF uses 1-indexed arrays, so we adjust the index.

        Args:
            f: File handle for writing job selection logic.
        """
        f.write("# Get current job label (LSF is 1-indexed)\n")
        f.write(f"JOB_INDEX=$(( ${self.array_task_id_var} - 1 ))\n")
        f.write("JOB_LABEL=${JOBS[$JOB_INDEX]}\n")
        f.write(
            f'echo "Running job: $JOB_LABEL (array task ${self.array_task_id_var})"\n\n'
        )

    def _write_scheduler_options(self, f):
        """
        Write LSF-specific directives to the submission script.

        Args:
            f: File handle for writing LSF directives.
        """
        f.write(f"#BSUB -J {self.job_name}{self.array_spec}\n")
        f.write(f"#BSUB -o {self.job_name}_%I.bsubout\n")
        f.write(f"#BSUB -e {self.job_name}_%I.bsuberr\n")
        f.write(f"#BSUB -n {self.server.num_cores}\n")
        f.write(f'#BSUB -R "rusage[mem={self.server.mem_gb}G]"\n')
        if self.server.num_gpus:
            f.write(f'#BSUB -R "select[ngpus>0] rusage[ngpus_excl_p={self.server.num_gpus}]"\n')
        if self.server.queue_name:
            f.write(f"#BSUB -q {self.server.queue_name}\n")
        if self.server.num_hours:
            f.write(f"#BSUB -W {self.server.num_hours}:00\n")
        if user_settings is not None:
            if user_settings.data.get("PROJECT"):
                f.write(f"#BSUB -P {user_settings.data['PROJECT']}\n")
            if user_settings.data.get("EMAIL"):
                f.write(f"#BSUB -u {user_settings.data['EMAIL']}\n")
                f.write("#BSUB -N\n")
        f.write("\n")
        f.write("\n")

    def _write_change_to_job_directory(self, f):
        """
        Write LSF-specific directory change command.

        Args:
            f: File handle for writing directory change command.
        """
        f.write("cd $LS_SUBCWD\n\n")

    def _get_submit_command(self) -> str:
        """Get LSF submission command."""
        return f"bsub < {self.submit_script}"

    def _parse_job_id(self, output: str) -> Optional[str]:
        """Parse job ID from LSF bsub output."""
        # LSF typically returns "Job <job_id> is submitted..."
        if "Job <" in output and ">" in output:
            start = output.index("<") + 1
            end = output.index(">")
            return output[start:end]
        return None
