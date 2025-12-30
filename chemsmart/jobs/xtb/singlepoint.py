"""
xTB single point job implementation.

This module contains the xTB single point energy calculation job class.
"""

import logging

from chemsmart.jobs.xtb.job import XTBJob

logger = logging.getLogger(__name__)


class XTBSinglePointJob(XTBJob):
    """
    xTB single point energy calculation job.

    This class runs xTB single point energy calculations without
    geometry optimization.

    Attributes:
        TYPE (str): Job type identifier ('xtbsp').
        molecule (Molecule): Molecular structure for the calculation.
        settings (XTBJobSettings): Job settings configured for single point.
        label (str): Job identifier used for file naming.
        jobrunner (JobRunner): Execution backend that runs the job.
        skip_completed (bool): If True, completed jobs are not rerun.
    """

    TYPE = "xtbsp"

    def __init__(
        self, molecule, settings=None, label=None, jobrunner=None, **kwargs
    ):
        """
        Initialize xTB single point job.

        Args:
            molecule: Molecule object for the calculation
            settings: xTB job settings (will be set to 'sp' type)
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

        # Ensure job type is set to single point
        self.settings.job_type = "sp"
