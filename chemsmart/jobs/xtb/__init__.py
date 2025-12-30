from .job import XTBJob
from .opt import XTBOptJob
from .singlepoint import XTBSinglePointJob
from .freq import XTBFreqJob

jobs = XTBJob.subclasses()

__all__ = [
    "XTBJob",
    "XTBOptJob",
    "XTBSinglePointJob",
    "XTBFreqJob",
    "jobs",
]
