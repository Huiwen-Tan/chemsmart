"""
Scheduler for parallel job submission via SLURM arrays.

This module provides the Scheduler class for managing parallel submission
of computational chemistry jobs using SLURM array functionality. It supports
automatic OPT → SP pipelines and configurable parallelism.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import List, Optional

logger = logging.getLogger(__name__)


class Scheduler(ABC):
    """
    Abstract base class for job schedulers.

    Provides the interface for scheduler implementations that handle
    parallel job submission to cluster schedulers.

    Attributes:
        jobs (list): List of jobs to be scheduled.
        max_parallel (int): Maximum number of parallel jobs.
        mode (str): Scheduling mode ('array' or 'worker').
        auto_sp (bool): Whether to automatically run SP after OPT.
    """

    def __init__(
        self,
        jobs: List,
        max_parallel: int = 10,
        mode: str = "array",
        auto_sp: bool = False,
    ):
        """
        Initialize the scheduler.

        Args:
            jobs: List of jobs to be scheduled.
            max_parallel: Maximum number of parallel jobs. Defaults to 10.
            mode: Scheduling mode ('array' or 'worker').
                Defaults to 'array'.
            auto_sp: Whether to automatically run SP after OPT.
                Defaults to False.
        """
        self.jobs = jobs
        self.max_parallel = max_parallel
        self.mode = mode
        self.auto_sp = auto_sp

    @property
    def num_jobs(self) -> int:
        """Get the number of jobs to be scheduled."""
        return len(self.jobs)

    @abstractmethod
    def render_script(self) -> str:
        """
        Render the submission script for the scheduler.

        Returns:
            str: The rendered submission script content.
        """
        raise NotImplementedError

    @abstractmethod
    def submit(self, test: bool = False) -> Optional[str]:
        """
        Submit the jobs to the scheduler.

        Args:
            test: If True, only write script without submitting.

        Returns:
            Optional[str]: Job ID if submitted, None if test mode.
        """
        raise NotImplementedError


class SLURMArrayScheduler(Scheduler):
    """
    SLURM array job scheduler.

    Implements parallel job submission using SLURM array functionality.
    Each array task runs a single job (or OPT→SP pipeline if auto_sp is True).

    This scheduler generates a single SLURM submission script that uses
    the SLURM_ARRAY_TASK_ID to index into the list of jobs, avoiding
    queue flooding from many independent sbatch submissions.

    Attributes:
        jobs (list): List of jobs to be scheduled.
        max_parallel (int): Maximum concurrent array tasks.
        mode (str): Always 'array' for this scheduler.
        auto_sp (bool): If True, run SP calculation after OPT completes.
        server: Server configuration for SLURM submission.
        job_labels (list[str]): Labels for each job in the array.
    """

    def __init__(
        self,
        jobs: List,
        server,
        max_parallel: int = 10,
        auto_sp: bool = False,
        job_name: str = "chemsmart_array",
        **kwargs,
    ):
        """
        Initialize the SLURM array scheduler.

        Args:
            jobs: List of jobs to be scheduled.
            server: Server configuration with SLURM settings.
            max_parallel: Maximum concurrent array tasks. Defaults to 10.
            auto_sp: Run SP after OPT for each task. Defaults to False.
            job_name: Base name for the SLURM job.
                Defaults to 'chemsmart_array'.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(
            jobs=jobs, max_parallel=max_parallel, mode="array", auto_sp=auto_sp
        )
        self.server = server
        self.job_name = job_name
        self.kwargs = kwargs

    @property
    def job_labels(self) -> List[str]:
        """Get the labels for all jobs in the array."""
        return [job.label for job in self.jobs]

    @property
    def array_spec(self) -> str:
        """
        Get the SLURM array specification string.

        Returns:
            str: Array spec like '0-9%5' for 10 jobs with max 5 concurrent.
        """
        if self.num_jobs == 0:
            return "0-0"
        # SLURM arrays are 0-indexed
        array_range = f"0-{self.num_jobs - 1}"
        if self.max_parallel and self.max_parallel < self.num_jobs:
            array_range += f"%{self.max_parallel}"
        return array_range

    def render_script(self) -> str:
        """
        Render the SLURM array submission script.

        Generates a bash script with SLURM directives that uses
        SLURM_ARRAY_TASK_ID to select which job to run.

        Returns:
            str: Complete SLURM submission script content.
        """
        lines = []

        # Bash header
        lines.append("#!/bin/bash")
        lines.append("")

        # SLURM directives
        lines.append(f"#SBATCH --job-name={self.job_name}")
        lines.append(f"#SBATCH --array={self.array_spec}")
        lines.append(f"#SBATCH --output={self.job_name}_%A_%a.slurmout")
        lines.append(f"#SBATCH --error={self.job_name}_%A_%a.slurmerr")

        if self.server.num_gpus:
            lines.append(f"#SBATCH --gres=gpu:{self.server.num_gpus}")

        lines.append(
            f"#SBATCH --nodes=1 --ntasks-per-node={self.server.num_cores} "
            f"--mem={self.server.mem_gb}G"
        )

        if self.server.queue_name:
            lines.append(f"#SBATCH --partition={self.server.queue_name}")

        if self.server.num_hours:
            lines.append(f"#SBATCH --time={self.server.num_hours}:00:00")

        lines.append("")
        lines.append("")

        # Change to submission directory
        lines.append("cd $SLURM_SUBMIT_DIR")
        lines.append("")

        # Job mapping - create array of job labels
        lines.append("# Job labels array")
        lines.append("JOBS=(")
        for label in self.job_labels:
            lines.append(f'    "{label}"')
        lines.append(")")
        lines.append("")

        # Get current job label from array index
        lines.append("# Get current job label")
        lines.append("JOB_LABEL=${JOBS[$SLURM_ARRAY_TASK_ID]}")
        lines.append(
            'echo "Running job: $JOB_LABEL (array task $SLURM_ARRAY_TASK_ID)"'
        )
        lines.append("")

        # Run the job using chemsmart run script
        lines.append("# Execute the job")
        lines.append("if [ -f \"chemsmart_run_${JOB_LABEL}.py\" ]; then")
        lines.append("    chmod +x chemsmart_run_${JOB_LABEL}.py")
        lines.append("    python chemsmart_run_${JOB_LABEL}.py")
        lines.append("else")
        lines.append(
            '    echo "Error: Run script not found for job $JOB_LABEL"'
        )
        lines.append("    exit 1")
        lines.append("fi")
        lines.append("")

        # Auto-SP pipeline if enabled
        if self.auto_sp:
            lines.append(
                "# Auto SP pipeline - run SP after OPT completes"
            )
            lines.append("if [ $? -eq 0 ]; then")
            lines.append('    SP_SCRIPT="chemsmart_run_${JOB_LABEL}_sp.py"')
            lines.append('    if [ -f "$SP_SCRIPT" ]; then')
            lines.append(
                '        echo "Running SP calculation for $JOB_LABEL"'
            )
            lines.append('        chmod +x "$SP_SCRIPT"')
            lines.append('        python "$SP_SCRIPT"')
            lines.append("    fi")
            lines.append("fi")
            lines.append("")

        lines.append("wait")

        return "\n".join(lines)

    @property
    def script_filename(self) -> str:
        """Get the filename for the submission script."""
        return f"chemsmart_array_sub_{self.job_name}.sh"

    def write_script(self, directory: Optional[str] = None) -> str:
        """
        Write the submission script to a file.

        Args:
            directory: Directory to write the script. Defaults to current dir.

        Returns:
            str: Path to the written script file.
        """
        script_content = self.render_script()

        if directory is None:
            directory = os.getcwd()

        script_path = os.path.join(directory, self.script_filename)

        with open(script_path, "w") as f:
            f.write(script_content)

        logger.info(f"Written SLURM array script to: {script_path}")
        return script_path

    def submit(self, test: bool = False) -> Optional[str]:
        """
        Submit the SLURM array job.

        Args:
            test: If True, only write script without submitting.

        Returns:
            Optional[str]: Job ID if submitted, None if test mode.
        """
        import shlex
        import subprocess

        # Write the submission script
        script_path = self.write_script()

        if test:
            logger.info(
                f"Test mode: script written to {script_path}, not submitted."
            )
            return None

        # Submit using sbatch
        command = f"sbatch {script_path}"
        logger.info(f"Submitting SLURM array job: {command}")

        try:
            result = subprocess.run(
                shlex.split(command),
                capture_output=True,
                text=True,
                check=True,
            )
            # Parse job ID from sbatch output
            # (typically "Submitted batch job XXXXX")
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


def parse_conformers_from_jobs(jobs: List) -> List[str]:
    """
    Parse conformer labels from a list of jobs.

    Utility function to extract labels from job objects for
    use in scheduler configuration.

    Args:
        jobs: List of job objects with label attribute.

    Returns:
        list[str]: List of job labels.
    """
    return [job.label for job in jobs if hasattr(job, "label")]
