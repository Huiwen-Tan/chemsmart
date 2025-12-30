"""
XTB Single Point Job Implementation.
"""

from chemsmart.jobs.xtb.job import XTBJob


class XTBSinglePointJob(XTBJob):
    """Single point energy calculation job using xTB."""
    
    TYPE = "xtb_sp"

    def __init__(self, molecule, settings, label, jobrunner=None, **kwargs):
        super().__init__(
            molecule=molecule,
            settings=settings,
            label=label,
            jobrunner=jobrunner,
            **kwargs,
        )
