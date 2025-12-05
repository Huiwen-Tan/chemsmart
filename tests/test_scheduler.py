"""
Tests for the Scheduler module.

This module tests SLURM array script rendering and parallel job submission
functionality for conformer jobs.
"""

import os
import tempfile

import pytest

from chemsmart.jobs.scheduler import SLURMArrayScheduler


class MockJob:
    """Mock job class for testing."""

    def __init__(self, label: str):
        self.label = label


class MockServer:
    """Mock server class for testing."""

    def __init__(
        self,
        num_cores=64,
        num_gpus=0,
        mem_gb=128,
        num_hours=24,
        queue_name="normal",
    ):
        self.num_cores = num_cores
        self.num_gpus = num_gpus
        self.mem_gb = mem_gb
        self.num_hours = num_hours
        self.queue_name = queue_name


class TestSLURMArrayScheduler:
    """Tests for SLURM array scheduler."""

    @pytest.fixture
    def mock_jobs(self):
        """Create a list of mock jobs for testing (100 conformers)."""
        return [MockJob(f"mol_c{i}") for i in range(1, 101)]

    @pytest.fixture
    def mock_server(self):
        """Create a mock server configuration."""
        return MockServer()

    def test_scheduler_initialization(self, mock_jobs, mock_server):
        """Test scheduler initializes correctly with defaults."""
        scheduler = SLURMArrayScheduler(
            jobs=mock_jobs, server=mock_server, max_parallel=4
        )

        assert scheduler.num_jobs == 100
        assert scheduler.max_parallel == 4

    def test_array_spec_with_parallel_limit(self, mock_jobs, mock_server):
        """Test array spec with 100 jobs and 4 parallel nodes."""
        scheduler = SLURMArrayScheduler(
            jobs=mock_jobs, server=mock_server, max_parallel=4
        )

        # 100 jobs with max 4 concurrent
        assert scheduler.array_spec == "0-99%4"

    def test_array_spec_without_limit(self, mock_server):
        """Test array spec generation without parallel limit."""
        jobs = [MockJob(f"job{i}") for i in range(5)]
        scheduler = SLURMArrayScheduler(
            jobs=jobs, server=mock_server, max_parallel=100
        )

        # max_parallel > num_jobs, so no limit suffix
        assert scheduler.array_spec == "0-4"

    def test_array_spec_single_job(self, mock_server):
        """Test array spec for single job."""
        jobs = [MockJob("single_job")]
        scheduler = SLURMArrayScheduler(jobs=jobs, server=mock_server)

        assert scheduler.array_spec == "0-0"

    def test_render_script_contains_sbatch_directives(
        self, mock_jobs, mock_server
    ):
        """Test rendered script contains required SBATCH directives."""
        scheduler = SLURMArrayScheduler(
            jobs=mock_jobs,
            server=mock_server,
            job_name="conformer_opt",
            max_parallel=4,
        )

        script = scheduler.render_script()

        # Check SBATCH directives
        assert "#!/bin/bash" in script
        assert "#SBATCH --job-name=conformer_opt" in script
        assert "#SBATCH --array=0-99%4" in script
        assert "#SBATCH --output=conformer_opt_%A_%a.slurmout" in script
        assert "#SBATCH --error=conformer_opt_%A_%a.slurmerr" in script
        assert "#SBATCH --nodes=1" in script
        assert "#SBATCH --ntasks-per-node=64" in script
        assert "#SBATCH --mem=128G" in script
        assert "#SBATCH --partition=normal" in script
        assert "#SBATCH --time=24:00:00" in script

    def test_render_script_contains_job_labels(self, mock_jobs, mock_server):
        """Test rendered script contains job labels array."""
        scheduler = SLURMArrayScheduler(jobs=mock_jobs, server=mock_server)

        script = scheduler.render_script()

        # Check job labels are included
        assert "JOBS=(" in script
        assert '"mol_c1"' in script
        assert '"mol_c50"' in script
        assert '"mol_c100"' in script

    def test_render_script_uses_array_task_id(self, mock_jobs, mock_server):
        """Test rendered script uses SLURM_ARRAY_TASK_ID."""
        scheduler = SLURMArrayScheduler(jobs=mock_jobs, server=mock_server)

        script = scheduler.render_script()

        assert "SLURM_ARRAY_TASK_ID" in script
        assert "JOB_LABEL=${JOBS[$SLURM_ARRAY_TASK_ID]}" in script

    def test_render_script_with_gpu(self, mock_jobs):
        """Test rendered script includes GPU allocation."""
        server = MockServer(num_gpus=2)
        scheduler = SLURMArrayScheduler(jobs=mock_jobs, server=server)

        script = scheduler.render_script()

        assert "#SBATCH --gres=gpu:2" in script

    def test_write_script(self, mock_jobs, mock_server):
        """Test script is written to file correctly."""
        scheduler = SLURMArrayScheduler(
            jobs=mock_jobs, server=mock_server, job_name="test_write"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = scheduler.write_script(directory=tmpdir)

            assert os.path.exists(script_path)
            assert script_path.endswith("chemsmart_array_sub_test_write.sh")

            with open(script_path) as f:
                content = f.read()

            assert "#!/bin/bash" in content
            assert "#SBATCH --array=" in content

    def test_submit_test_mode(self, mock_jobs, mock_server):
        """Test submit in test mode doesn't actually submit."""
        scheduler = SLURMArrayScheduler(jobs=mock_jobs, server=mock_server)

        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = scheduler.submit(test=True)

                assert result is None
                # Script should still be written
                assert os.path.exists(scheduler.script_filename)
            finally:
                os.chdir(original_dir)


class TestSchedulerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_job_list(self):
        """Test scheduler with empty job list."""
        server = MockServer()
        scheduler = SLURMArrayScheduler(jobs=[], server=server)

        assert scheduler.num_jobs == 0
        # Empty job list should return empty string for array spec
        assert scheduler.array_spec == ""

    def test_empty_job_list_submit_raises(self):
        """Test that submitting empty job list raises ValueError."""
        server = MockServer()
        scheduler = SLURMArrayScheduler(jobs=[], server=server)

        with pytest.raises(ValueError, match="Cannot submit SLURM array"):
            scheduler.submit(test=False)

    def test_job_labels_property(self):
        """Test job_labels returns correct labels."""
        server = MockServer()
        jobs = [MockJob(f"conf{i}") for i in range(1, 6)]
        scheduler = SLURMArrayScheduler(jobs=jobs, server=server)

        labels = scheduler.job_labels
        assert labels == ["conf1", "conf2", "conf3", "conf4", "conf5"]
