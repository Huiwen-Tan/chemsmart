"""
Scheduler for parallel job submission via SLURM arrays.

This module provides the SLURMArrayScheduler class for managing parallel
submission of computational chemistry jobs using SLURM array functionality.
"""

import logging
import shlex
import subprocess

from chemsmart.settings.user import ChemsmartUserSettings

user_settings = ChemsmartUserSettings()

logger = logging.getLogger(__name__)


class SLURMArrayScheduler:
    """
    SLURM array job scheduler.

    Implements parallel job submission using SLURM array functionality.
    Each array task runs a single job. When a node finishes, the next
    job in the queue is automatically assigned to it.

    This scheduler generates a single SLURM submission script that uses
    the SLURM_ARRAY_TASK_ID to index into the list of jobs, avoiding
    queue flooding from many independent sbatch submissions.

    Attributes:
        jobs (list): List of jobs to be scheduled.
        max_parallel (int): Maximum concurrent array tasks (nodes).
        server: Server configuration for SLURM submission.
        job_labels (list[str]): Labels for each job in the array.
    """

    def __init__(
        self,
        jobs,
        server,
        max_parallel=None,
        job_name=None,
        **kwargs,
    ):
        """
        Initialize the SLURM array scheduler.

        Args:
            jobs: List of jobs to be scheduled.
            server: Server configuration with SLURM settings.
            max_parallel: Maximum concurrent array tasks (nodes).
            job_name: Base name for the SLURM job.
            **kwargs: Additional keyword arguments.
        """
        self.jobs = jobs
        self.max_parallel = max_parallel
        self.server = server
        self.job_name = job_name
        self.kwargs = kwargs

    @property
    def num_jobs(self):
        """Get the number of jobs to be scheduled."""
        return len(self.jobs)

    @property
    def job_labels(self):
        """Get the labels for all jobs in the array."""
        return [job.label for job in self.jobs]

    @property
    def array_spec(self):
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

    def _write_bash_header(self, f):
        """
        Write the bash shebang header to the script.

        Args:
            f: File handle for writing the script.
        """
        f.write("#!/bin/bash\n\n")

    def _write_scheduler_options(self, f):
        """
        Write SLURM-specific directives to the submission script.

        Args:
            f: File handle for writing SLURM directives.
        """
        f.write(f"#SBATCH --job-name={self.job_name}_%a\n")
        f.write(f"#SBATCH --array={self.array_spec}\n")
        f.write(f"#SBATCH --output={self.job_name}_%a.slurmout\n")
        f.write(f"#SBATCH --error={self.job_name}_%a.slurmerr\n")
        if self.server.num_gpus:
            f.write(f"#SBATCH --gres=gpu:{self.server.num_gpus}\n")
        f.write(
            f"#SBATCH --nodes=1 --ntasks-per-node={self.server.num_cores} --mem={self.server.mem_gb}G\n"
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

        Uses SLURM_SUBMIT_DIR environment variable to change to the
        job submission directory.

        Args:
            f: File handle for writing directory change command.
        """
        f.write("cd $SLURM_SUBMIT_DIR\n\n")

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
        f.write("JOB_LABEL=${JOBS[$SLURM_ARRAY_TASK_ID]}\n")
        f.write(
            'echo "Running job: $JOB_LABEL (array task $SLURM_ARRAY_TASK_ID)"\n\n'
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
        Write the complete SLURM array submission script.
        """
        with open(self.submit_script, "w") as f:
            logger.debug(
                f"Written SLURM array script to: {self.submit_script}"
            )
            self._write_bash_header(f)
            self._write_scheduler_options(f)
            self._write_change_to_job_directory(f)
            self._write_job_array_mapping(f)
            self._write_job_selection(f)
            self._write_job_execution(f)

    @property
    def submit_script(self):
        """Get the filename for the submission script."""
        if self.job_name is not None:
            return f"chemsmart_array_sub_{self.job_name}.sh"
        return "chemsmart_array_sub.sh"

    def submit(self, test=False):
        """
        Submit the SLURM array job.

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
            raise ValueError("Cannot submit SLURM array with no jobs")

        # Write the submission script
        self._write_script()

        if test:
            logger.info(
                f"Test mode: script written to {self.submit_script}, not submitted."
            )
            return None

        # Submit using sbatch
        command = f"sbatch {self.submit_script}"
        logger.info(f"Submitting SLURM array job: {command}")

        try:
            result = subprocess.run(
                shlex.split(command),
                capture_output=True,
                text=True,
                check=True,
            )

            output = result.stdout.strip()
            logger.info(f"SLURM submission output: {output}")

            # Extract job ID
            if "Submitted batch job" in output:
                job_id = output.split()[-1]
                logger.info(f"Submitted SLURM array job with ID: {job_id}")
                return job_id

            return output

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to submit SLURM array job: {e.stderr}")
            raise RuntimeError(f"SLURM submission failed: {e.stderr}") from e
