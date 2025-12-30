"""
xTB job module initialization.

This module provides xTB job functionality including various job types,
settings, and runners for xTB semi-empirical quantum chemistry calculations.
"""

from .job import XTBGeneralJob, XTBJob
from .opt import XTBOptJob
from .runner import XTBJobRunner
from .singlepoint import XTBSinglePointJob

# Get all available xTB job subclasses
jobs = XTBJob.subclasses()


__all__ = [
    "XTBJob",
    "XTBGeneralJob",
    "XTBOptJob",
    "XTBSinglePointJob",
    "XTBJobRunner",
    "jobs",
]
