"""
Submission of jobs to queuing system via cli.

This module provides command-line interface for submitting jobs to
various queuing systems and cluster schedulers. Supports parallel
submission of multiple jobs via SLURM arrays.
"""

import logging

import click

from chemsmart.cli.jobrunner import click_jobrunner_options
from chemsmart.cli.logger import logger_options
from chemsmart.cli.subcommands import subcommands
from chemsmart.jobs.runner import JobRunner
from chemsmart.settings.server import Server
from chemsmart.utils.cli import CtxObjArguments, MyGroup
from chemsmart.utils.logger import create_logger

logger = logging.getLogger(__name__)


@click.group(name="sub", cls=MyGroup)
@click.pass_context
@click_jobrunner_options
@logger_options
@click.option(
    "-t",
    "--time-hours",
    type=float,
    default=None,
    help="Time limit in hours for the job (e.g., 48.0).",
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
    help="If true, job will not be submitted; only run and submit "
    "scripts will be written.",
)
@click.option(
    "--print-command/--no-print-command",
    default=False,
    help="Print the generated command.",
)
@click.option(
    "-N",
    "--num-nodes",
    type=int,
    default=None,
    help="Number of parallel nodes for SLURM array submission. ",
)
def sub(
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
    time_hours,
    queue,
    verbose,
    test,
    print_command,
    num_nodes,
    **kwargs,
):
    """
    Main command for submitting chemsmart jobs to queuing systems.

    This command prepares and submits jobs to cluster schedulers with
    specified resource requirements and queue parameters.

    When -N/--num-nodes is specified, jobs with multiple sub-jobs
    (e.g., crest, traj, irc) will be submitted as a SLURM array job where
    N jobs run in parallel. When one finishes, the next automatically
    starts.

    Example:
        chemsmart sub -s server -N 4 -n 64 gaussian -p project \\
            -f crest_conformers.xyz -c 0 -m 1 crest -j opt

        This submits 4 parallel nodes, each with 64 processors.
    """
    # Set up logging
    if verbose:
        create_logger(stream=True, debug=True)
    else:
        create_logger(debug=debug, stream=stream)
    logger.info("Entering main program")

    # Instantiate the jobrunner with CLI options
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

    # Log the scratch value for debugging purposes
    logger.debug(f"Scratch value passed from CLI: {scratch}")

    # Store the jobrunner and other options in the context object
    ctx.ensure_object(dict)  # Ensure ctx.obj is initialized as a dict
    ctx.obj["jobrunner"] = jobrunner
    ctx.obj["num_nodes"] = num_nodes  # Store for parallel submission


@sub.result_callback(replace=True)
@click.pass_context
def process_pipeline(ctx, *args, **kwargs):  # noqa: PLR0915
    """
    Process the job for submission to queuing system.

    This callback function handles job submission by reconstructing
    command-line arguments and interfacing with the appropriate
    scheduler system. Supports parallel submission via SLURM arrays
    when -N/--num-nodes is specified.
    """

    def _clean_command(ctx):
        """
        Remove keywords used in sub.py but not in run.py.

        Specifically: Some keywords/options (like queue, verbose, etc.)
        are only relevant to sub.py and not applicable to run.py.
        """
        # Get "sub" command and assert that there is exactly one.
        command = next(
            (
                subcommand
                for subcommand in ctx.obj["subcommand"]
                if subcommand["name"] == "sub"
            ),
            None,
        )
        if not command:
            raise ValueError("No 'sub' command found in context.")

        # Find the keywords that are valid in sub.py
        # but should not be passed to run.py and remove those
        keywords_not_in_run = [
            "time_hours",
            "queue",
            "verbose",
            "test",
            "print_command",
            "num_nodes",
        ]

        for keyword in keywords_not_in_run:
            # Remove keyword if it exists
            command["kwargs"].pop(keyword, None)
        return ctx

    def _reconstruct_cli_args(ctx, job):
        """
        Get cli args that reconstruct the command line.

        Rebuilds the command-line arguments from the context object
        for job submission purposes.
        """
        commands = ctx.obj["subcommand"]

        args = CtxObjArguments(commands, entry_point="sub")
        cli_args = args.reconstruct_command_line()[
            1:
        ]  # remove the first element 'sub'
        if kwargs.get("print_command"):
            print(cli_args)
        return cli_args

    def _process_single_job(job):
        if kwargs.get("test"):
            logger.warning('Not submitting as "test" flag specified.')

        cli_args = _reconstruct_cli_args(ctx, job)

        server = Server.from_servername(kwargs.get("server"))
        server.submit(job=job, test=kwargs.get("test"), cli_args=cli_args)

    def _process_parallel_jobs(job, num_nodes):
        """
        Process multiple jobs in parallel using SLURM array.

        For jobs with multiple sub-jobs (crest, traj, irc), this submits
        a SLURM array job where num_nodes jobs run in parallel.
        When one finishes, the next automatically starts.
        """
        from chemsmart.jobs.scheduler import SLURMArrayScheduler

        # Extract individual jobs from the container job
        if hasattr(job, "all_conformers_jobs"):
            all_jobs = job.all_conformers_jobs
            logger.info(
                f"Found {len(all_jobs)} conformer jobs for parallel submission"
            )
        elif hasattr(job, "all_structures_run_jobs"):
            all_jobs = job.all_structures_run_jobs
            logger.info(
                f"Found {len(all_jobs)} structure jobs for parallel submission"
            )
        else:
            # Single job - fall back to single submission
            logger.info(
                "Job does not contain multiple conformers, "
                "submitting as single job"
            )
            _process_single_job(job)
            return

        # Set jobrunner for all jobs
        jobrunner = ctx.obj["jobrunner"]
        for j in all_jobs:
            j.jobrunner = jobrunner

        # Reconstruct CLI args once (same for all jobs in the array)
        cli_args = _reconstruct_cli_args(ctx, job)

        # Write run scripts for each individual job
        server = Server.from_servername(kwargs.get("server"))
        for j in all_jobs:
            # Write only the run script, not submit
            server.submit(job=j, test=True, cli_args=cli_args)

        # Create and submit SLURM array job
        scheduler = SLURMArrayScheduler(
            jobs=all_jobs,
            server=server,
            max_parallel=num_nodes,
            job_name=job.label,
        )

        logger.info(
            f"Submitting SLURM array job with {len(all_jobs)} tasks, "
            f"max {num_nodes} parallel"
        )

        if kwargs.get("test"):
            logger.warning('Not submitting as "test" flag specified.')
            scheduler.submit(test=True)
        else:
            job_id = scheduler.submit(test=False)
            logger.info(f"Submitted SLURM array job: {job_id}")

    ctx = _clean_command(ctx)
    jobrunner = ctx.obj["jobrunner"]
    num_nodes = ctx.obj.get("num_nodes")
    job = args[0]
    job.jobrunner = jobrunner

    # Check if parallel submission is requested
    if num_nodes is not None and num_nodes > 0:
        _process_parallel_jobs(job, num_nodes)
    else:
        _process_single_job(job=job)


for subcommand in subcommands:
    sub.add_command(subcommand)
