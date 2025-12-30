"""
XTB Frequency (Hessian) Job Implementation.
"""

from chemsmart.jobs.xtb.job import XTBJob


class XTBFreqJob(XTBJob):
    """Frequency calculation (Hessian) job using xTB."""
    
    TYPE = "xtb_freq"

    def __init__(self, molecule, settings, label, jobrunner=None, **kwargs):
        super().__init__(
            molecule=molecule,
            settings=settings,
            label=label,
            jobrunner=jobrunner,
            **kwargs,
        )
