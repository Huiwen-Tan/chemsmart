"""
xTB geometry optimization job implementation.

This module contains the xTB geometry optimization job class.
"""

import logging

from chemsmart.jobs.xtb.job import XTBJob

logger = logging.getLogger(__name__)


class XTBOptJob(XTBJob):
    """
    xTB geometry optimization job.

    This class runs xTB geometry optimizations to find local minima
    or optimized molecular structures.

    Attributes:
        TYPE (str): Job type identifier ('xtbopt').
        molecule (Molecule): Molecular structure for the calculation.
        settings (XTBJobSettings): Job settings configured for optimization.
        label (str): Job identifier used for file naming.
        jobrunner (JobRunner): Execution backend that runs the job.
        skip_completed (bool): If True, completed jobs are not rerun.
    """

    TYPE = "xtbopt"

    def __init__(
        self, molecule, settings=None, label=None, jobrunner=None, **kwargs
    ):
        """
        Initialize xTB optimization job.

        Args:
            molecule: Molecule object for the calculation
            settings: xTB job settings (will be set to 'opt' type)
            label: Job label (optional)
            jobrunner: Job runner instance (optional)
            **kwargs: Additional keyword arguments
        """
        super().__init__(
            molecule=molecule,
            settings=settings,
            label=label,
            jobrunner=jobrunner,
            **kwargs,
        )

        # Ensure job type is set to optimization
        self.settings.job_type = "opt"
