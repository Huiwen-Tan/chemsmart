"""
Batch submission of jobs to queuing system via CLI.

This module provides command-line interface for submitting multiple jobs
in parallel using SLURM array functionality.
"""

import logging

import click

from chemsmart.cli.jobrunner import click_jobrunner_options
from chemsmart.cli.logger import logger_options
from chemsmart.cli.subcommands import subcommands
from chemsmart.jobs.runner import JobRunner
from chemsmart.settings.server import Server
from chemsmart.utils.cli import MyGroup
from chemsmart.utils.logger import create_logger

logger = logging.getLogger(__name__)


def click_scheduler_options(f):
    """
    Decorator for scheduler-related CLI options.

    Adds options for parallel job submission via SLURM arrays.
    """
    import functools

    @click.option(
        "--max-parallel",
        "-P",
        type=int,
        default=10,
        help="Maximum number of parallel jobs in array. Defaults to 10.",
    )
    @click.option(
        "--mode",
        "-M",
        type=click.Choice(["array", "worker"], case_sensitive=False),
        default="array",
        help="Scheduling mode: 'array' for SLURM arrays (default), "
        "'worker' for worker-pool mode (future).",
    )
    @click.option(
        "--auto-sp/--no-auto-sp",
        default=False,
        help="Automatically run SP calculation after OPT completes in each "
        "array task. Default: disabled.",
    )
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper


@click.group(name="batch", cls=MyGroup)
@click.pass_context
@click_jobrunner_options
@logger_options
@click_scheduler_options
@click.option(
    "-t",
    "--time-hours",
    type=float,
    default=None,
    help="Time limit in hours for each job (e.g., 48.0).",
)
@click.option("-q", "--queue", type=str, help="Queue name for job submission.")
@click.option(
    "-v/",
    "--verbose/--no-verbose",
    default=False,
    help="Turn on logging to stream output and debug logging.",
)
@click.option(
    "--test/--no-test",
    default=False,
    help="If true, jobs will not be submitted; only scripts will be written.",
)
@click.option(
    "-n",
    "--job-name",
    type=str,
    default="chemsmart_batch",
    help="Base name for the batch job.",
)
def batch(
    ctx,
    server,
    num_cores,
    num_gpus,
    mem_gb,
    fake,
    scratch,
    delete_scratch,
    debug,
    stream,
    max_parallel,
    mode,
    auto_sp,
    time_hours,
    queue,
    verbose,
    test,
    job_name,
    **kwargs,
):
    """
    Batch submission of multiple jobs using SLURM array.

    This command prepares and submits multiple jobs as a single SLURM
    array job, avoiding queue flooding from many independent submissions.

    The default mode is 'array', which uses SLURM array tasks.
    Each array task runs OPT (and optionally SP) for one job.

    Example usage:
        chemsmart batch gaussian -p project -f conformers.xyz crest opt
    """
    # Set up logging
    if verbose:
        create_logger(stream=True, debug=True)
    else:
        create_logger(debug=debug, stream=stream)
    logger.info("Entering batch submission mode")

    # Instantiate server with CLI options
    if server is not None:
        server = Server.from_servername(server)
        if time_hours is not None:
            server.num_hours = time_hours
        if queue is not None:
            server.queue_name = queue

    jobrunner = JobRunner(
        server=server,
        scratch=scratch,
        delete_scratch=delete_scratch,
        fake=fake,
        num_cores=num_cores,
        num_gpus=num_gpus,
        mem_gb=mem_gb,
    )

    logger.debug(f"Scratch value passed from CLI: {scratch}")

    # Store options in context
    ctx.ensure_object(dict)
    ctx.obj["jobrunner"] = jobrunner
    ctx.obj["server"] = server
    ctx.obj["max_parallel"] = max_parallel
    ctx.obj["mode"] = mode
    ctx.obj["auto_sp"] = auto_sp
    ctx.obj["test"] = test
    ctx.obj["job_name"] = job_name


@batch.result_callback(replace=True)
@click.pass_context
def process_batch_pipeline(ctx, *args, **kwargs):
    """
    Process multiple jobs for batch submission.

    This callback handles batch job submission using the scheduler
    to create a SLURM array job from the list of individual jobs.
    """
    from chemsmart.jobs.scheduler import SLURMArrayScheduler

    jobrunner = ctx.obj["jobrunner"]
    server = ctx.obj["server"]
    max_parallel = ctx.obj["max_parallel"]
    mode = ctx.obj["mode"]
    auto_sp = ctx.obj["auto_sp"]
    test = ctx.obj["test"]
    job_name = ctx.obj["job_name"]

    # Get the job(s) from the subcommand
    # args[0] can be a single job or a job with multiple sub-jobs
    job = args[0]

    # Extract all jobs to submit
    # For crest/traj jobs, extract all conformer jobs
    if hasattr(job, "all_conformers_jobs"):
        jobs = job.all_conformers_jobs
        logger.info(f"Found {len(jobs)} conformer jobs for batch submission")
    elif hasattr(job, "all_structures_run_jobs"):
        jobs = job.all_structures_run_jobs
        logger.info(f"Found {len(jobs)} structure jobs for batch submission")
    else:
        # Single job
        jobs = [job]
        logger.info("Submitting single job via batch mode")

    # Set jobrunner for all jobs
    for j in jobs:
        j.jobrunner = jobrunner

    if mode == "array":
        logger.info(f"Using SLURM array mode with max_parallel={max_parallel}")
        scheduler = SLURMArrayScheduler(
            jobs=jobs,
            server=server,
            max_parallel=max_parallel,
            auto_sp=auto_sp,
            job_name=job_name,
        )

        # Write run scripts for each job first
        _write_run_scripts_for_jobs(jobs, ctx)

        # Submit the array job
        job_id = scheduler.submit(test=test)

        if job_id:
            logger.info(f"Submitted SLURM array job with ID: {job_id}")
        elif test:
            logger.info(
                "Test mode: scripts written, not submitted. "
                f"Script: {scheduler.script_filename}"
            )
    elif mode == "worker":
        logger.warning(
            "Worker-pool mode is not yet implemented. "
            "Use 'array' mode instead."
        )
        raise NotImplementedError(
            "Worker-pool mode will be added in follow-up PRs."
        )


def _write_run_scripts_for_jobs(jobs, ctx):
    """
    Write run scripts for all jobs in the batch.

    Creates the individual chemsmart_run_<label>.py scripts that will
    be executed by each array task.
    """
    from chemsmart.settings.submitters import RunScript

    logger.info(f"Writing run scripts for {len(jobs)} jobs")

    for job in jobs:
        # Reconstruct CLI args for this specific job
        # For now, use a simplified approach with the job label
        cli_args = _get_cli_args_for_job(job, ctx)

        run_script = RunScript(
            filename=f"chemsmart_run_{job.label}.py",
            cli_args=cli_args,
        )
        run_script.write()
        logger.debug(f"Written run script for job: {job.label}")


def _get_cli_args_for_job(job, ctx):
    """
    Get CLI arguments for running a specific job.

    Constructs the CLI arguments needed to run this job via
    'chemsmart run'.

    Note: This is a simplified implementation. The reconstructed args
    may need modification for individual conformer jobs in multi-job
    containers like crest or traj.
    """
    from chemsmart.utils.cli import CtxObjArguments

    # Get the subcommand chain from context
    if "subcommand" in ctx.obj:
        commands = ctx.obj["subcommand"]
        args = CtxObjArguments(commands, entry_point="batch")
        cli_args = args.reconstruct_command_line()
        # Remove 'batch' entry point if present
        if cli_args and cli_args[0] == "batch":
            base_args = cli_args[1:]
        else:
            base_args = cli_args
    else:
        base_args = []

    # For multi-job containers, we need to modify args to point to
    # the specific conformer. This is a simplified implementation.
    # In a full implementation, we would reconstruct the exact CLI
    # for each individual job.

    return base_args


# Add subcommands to batch group
for subcommand in subcommands:
    batch.add_command(subcommand)
