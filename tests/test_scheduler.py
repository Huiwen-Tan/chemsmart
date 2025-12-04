"""
Tests for the Scheduler module.

This module tests conformer parsing and SLURM array script rendering
functionality for parallel job submission.
"""

import os
import tempfile

import pytest

from chemsmart.jobs.scheduler import (
    SLURMArrayScheduler,
    parse_conformers_from_jobs,
)


class MockJob:
    """Mock job class for testing."""

    def __init__(self, label: str):
        self.label = label


class MockServer:
    """Mock server class for testing."""

    def __init__(
        self,
        num_cores=16,
        num_gpus=0,
        mem_gb=64,
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
        """Create a list of mock jobs for testing."""
        return [
            MockJob("mol1_opt"),
            MockJob("mol2_opt"),
            MockJob("mol3_opt"),
            MockJob("mol4_opt"),
            MockJob("mol5_opt"),
        ]

    @pytest.fixture
    def mock_server(self):
        """Create a mock server configuration."""
        return MockServer()

    def test_scheduler_initialization(self, mock_jobs, mock_server):
        """Test scheduler initializes correctly with defaults."""
        scheduler = SLURMArrayScheduler(
            jobs=mock_jobs, server=mock_server, max_parallel=5
        )

        assert scheduler.num_jobs == 5
        assert scheduler.max_parallel == 5
        assert scheduler.mode == "array"
        assert scheduler.auto_sp is False

    def test_scheduler_with_auto_sp(self, mock_jobs, mock_server):
        """Test scheduler with auto_sp enabled."""
        scheduler = SLURMArrayScheduler(
            jobs=mock_jobs, server=mock_server, auto_sp=True
        )

        assert scheduler.auto_sp is True

    def test_job_labels_property(self, mock_jobs, mock_server):
        """Test job_labels returns correct labels."""
        scheduler = SLURMArrayScheduler(jobs=mock_jobs, server=mock_server)

        labels = scheduler.job_labels
        expected = [
            "mol1_opt", "mol2_opt", "mol3_opt", "mol4_opt", "mol5_opt"
        ]
        assert labels == expected

    def test_array_spec_without_limit(self, mock_jobs, mock_server):
        """Test array spec generation without parallel limit."""
        scheduler = SLURMArrayScheduler(
            jobs=mock_jobs, server=mock_server, max_parallel=100
        )

        # max_parallel > num_jobs, so no limit suffix
        assert scheduler.array_spec == "0-4"

    def test_array_spec_with_limit(self, mock_jobs, mock_server):
        """Test array spec generation with parallel limit."""
        scheduler = SLURMArrayScheduler(
            jobs=mock_jobs, server=mock_server, max_parallel=2
        )

        assert scheduler.array_spec == "0-4%2"

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
            job_name="test_array",
            max_parallel=3,
        )

        script = scheduler.render_script()

        # Check SBATCH directives
        assert "#!/bin/bash" in script
        assert "#SBATCH --job-name=test_array" in script
        assert "#SBATCH --array=0-4%3" in script
        assert "#SBATCH --output=test_array_%A_%a.slurmout" in script
        assert "#SBATCH --error=test_array_%A_%a.slurmerr" in script
        assert "#SBATCH --nodes=1" in script
        assert "#SBATCH --partition=normal" in script
        assert "#SBATCH --time=24:00:00" in script

    def test_render_script_contains_job_labels(self, mock_jobs, mock_server):
        """Test rendered script contains job labels array."""
        scheduler = SLURMArrayScheduler(jobs=mock_jobs, server=mock_server)

        script = scheduler.render_script()

        # Check job labels are included
        assert "JOBS=(" in script
        assert '"mol1_opt"' in script
        assert '"mol2_opt"' in script
        assert '"mol3_opt"' in script

    def test_render_script_uses_array_task_id(self, mock_jobs, mock_server):
        """Test rendered script uses SLURM_ARRAY_TASK_ID."""
        scheduler = SLURMArrayScheduler(jobs=mock_jobs, server=mock_server)

        script = scheduler.render_script()

        assert "SLURM_ARRAY_TASK_ID" in script
        assert "JOB_LABEL=${JOBS[$SLURM_ARRAY_TASK_ID]}" in script

    def test_render_script_with_auto_sp(self, mock_jobs, mock_server):
        """Test rendered script includes auto SP pipeline when enabled."""
        scheduler = SLURMArrayScheduler(
            jobs=mock_jobs, server=mock_server, auto_sp=True
        )

        script = scheduler.render_script()

        # Check auto SP pipeline is included
        assert "Auto SP pipeline" in script
        assert "_sp.py" in script

    def test_render_script_without_auto_sp(self, mock_jobs, mock_server):
        """Test rendered script excludes auto SP when disabled."""
        scheduler = SLURMArrayScheduler(
            jobs=mock_jobs, server=mock_server, auto_sp=False
        )

        script = scheduler.render_script()

        # Auto SP pipeline should not be present
        assert "Auto SP pipeline" not in script

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


class TestParseConformersFromJobs:
    """Tests for conformer parsing utility."""

    def test_parse_conformers_basic(self):
        """Test basic conformer label parsing."""
        jobs = [MockJob("conf1"), MockJob("conf2"), MockJob("conf3")]

        labels = parse_conformers_from_jobs(jobs)

        assert labels == ["conf1", "conf2", "conf3"]

    def test_parse_conformers_empty_list(self):
        """Test parsing empty job list."""
        labels = parse_conformers_from_jobs([])

        assert labels == []

    def test_parse_conformers_with_mixed_objects(self):
        """Test parsing with objects that may not have label attribute."""

        class NoLabelJob:
            pass

        jobs = [MockJob("has_label"), NoLabelJob(), MockJob("also_has_label")]

        labels = parse_conformers_from_jobs(jobs)

        # Should only include jobs with label attribute
        assert labels == ["has_label", "also_has_label"]


class TestSchedulerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_job_list(self):
        """Test scheduler with empty job list."""
        server = MockServer()
        scheduler = SLURMArrayScheduler(jobs=[], server=server)

        assert scheduler.num_jobs == 0
        assert scheduler.array_spec == "0-0"

    def test_single_job(self):
        """Test scheduler with single job."""
        server = MockServer()
        jobs = [MockJob("single")]
        scheduler = SLURMArrayScheduler(jobs=jobs, server=server)

        assert scheduler.num_jobs == 1
        script = scheduler.render_script()
        assert "#SBATCH --array=0-0" in script

    def test_max_parallel_greater_than_jobs(self):
        """Test max_parallel greater than number of jobs."""
        server = MockServer()
        jobs = [MockJob("job1"), MockJob("job2")]
        scheduler = SLURMArrayScheduler(
            jobs=jobs, server=server, max_parallel=100
        )

        # Should not include parallel limit
        assert scheduler.array_spec == "0-1"

    def test_max_parallel_equals_jobs(self):
        """Test max_parallel equals number of jobs."""
        server = MockServer()
        jobs = [MockJob("job1"), MockJob("job2"), MockJob("job3")]
        scheduler = SLURMArrayScheduler(
            jobs=jobs, server=server, max_parallel=3
        )

        # Should not include parallel limit
        assert scheduler.array_spec == "0-2"
