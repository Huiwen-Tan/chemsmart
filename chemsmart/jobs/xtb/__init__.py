"""
xTB job module initialization.

This module provides xTB job functionality including various job types,
settings, and runners for xTB semi-empirical quantum chemistry calculations.
"""

from .job import XTBJob, XTBOptJob, XTBSinglePointJob
from .runner import XTBJobRunner

# Get all available xTB job subclasses
jobs = XTBJob.subclasses()


__all__ = [
    "XTBJob",
    "XTBSinglePointJob",
    "XTBOptJob",
    "XTBJobRunner",
    "jobs",
]
