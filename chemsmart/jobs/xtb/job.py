"""
xTB job implementation.

This module contains the main xTB job classes for running semi-empirical
quantum chemistry calculations using the xTB program package.
"""

import logging
import os
from typing import Type

from chemsmart.io.molecules.structure import Molecule
from chemsmart.jobs.job import Job
from chemsmart.jobs.runner import JobRunner
from chemsmart.settings.xtb import XTBJobSettings
from chemsmart.utils.utils import string2index_1based

logger = logging.getLogger(__name__)


class XTBJob(Job):
    """
    Base xTB job class.

    This class provides the foundation for all xTB semi-empirical
    quantum chemistry calculations including setup, execution, and output handling.

    Attributes:
        PROGRAM (str): Program identifier ('XTB').
        molecule (Molecule): Molecular structure used for the calculation.
        settings (XTBJobSettings): Configuration options for the job.
        label (str): Job identifier used for file naming.
        jobrunner (JobRunner): Execution backend that runs the job.
        skip_completed (bool): If True, completed jobs are not rerun.
    """

    PROGRAM = "XTB"

    def __init__(
        self, molecule, settings=None, label=None, jobrunner=None, **kwargs
    ):
        """
        Initialize XTBJob.

        Args:
            molecule: Molecule object for the calculation
            settings: XTBJobSettings instance
            label: Job label for identification
            jobrunner: Job runner instance
            **kwargs: Additional keyword arguments
        """
        super().__init__(
            molecule=molecule, label=label, jobrunner=jobrunner, **kwargs
        )

        # Validate settings type
        if settings is not None and not isinstance(settings, XTBJobSettings):
            raise ValueError(
                f"Settings must be instance of {XTBJobSettings} for {self}, "
                f"but is {settings} instead!"
            )

        # Validate molecule type
        if not isinstance(molecule, Molecule):
            raise ValueError(
                f"Molecule must be instance of Molecule for {self}, but is "
                f"{molecule} instead!"
            )

        # Store validated parameters
        self.molecule = molecule.copy() if molecule is not None else None
        self.settings = settings.copy() if settings else XTBJobSettings.default()

        # Set default label if not provided
        if label is None:
            label = molecule.get_chemical_formula(empirical=True)
        self.label = label

    @classmethod
    def settings_class(cls) -> Type[XTBJobSettings]:
        """
        Return the settings class for this job type.

        Returns:
            XTBJobSettings class
        """
        return XTBJobSettings

    @property
    def inputfile(self):
        """
        Get the input file path for the xTB job.

        Returns:
            str: Absolute path to the input file (xyz format)
        """
        inputfile = self.label + ".xyz"
        return os.path.join(self.folder, inputfile)

    @property
    def outputfile(self):
        """
        Get the output file path for the xTB job.

        Returns:
            str: Absolute path to the main output file
        """
        outputfile = self.label + ".out"
        return os.path.join(self.folder, outputfile)

    @property
    def errfile(self):
        """
        Get the error file path for the xTB job.

        Returns:
            str: Absolute path to the error file
        """
        errfile = self.label + ".err"
        return os.path.join(self.folder, errfile)

    def _backup_files(self, **kwargs):
        """
        Create backup of important files.

        Args:
            **kwargs: Additional arguments for backup operation
        """
        folder = self._create_backup_folder_name()
        self.backup_file(self.inputfile, folder=folder, **kwargs)
        self.backup_file(self.outputfile, folder=folder, **kwargs)

    def _output(self):
        """
        Get the output object if the output file exists.

        Returns:
            XTBOutput or None: Output object if file exists, None otherwise
        """
        if not os.path.exists(self.outputfile):
            logger.debug(f"Output file not found: {self.outputfile}")
            return None

        try:
            from chemsmart.io.xtb.output import XTBOutput

            return XTBOutput(self.outputfile, job_folder=self.folder)
        except Exception as e:
            logger.error(f"Error creating XTBOutput object: {e}")
            return None

    def _run(self, **kwargs):
        """
        Run the job using the assigned jobrunner.

        Args:
            **kwargs: Additional arguments for job execution
        """
        logger.info(f"Running XTBJob {self} with jobrunner {self.jobrunner}")
        self.jobrunner.run(self, **kwargs)

    @classmethod
    def from_filename(
        cls,
        filename,
        settings=None,
        index="-1",
        label=None,
        jobrunner=None,
        **kwargs,
    ):
        """
        Create xTB job from molecular structure file.

        Args:
            filename: Path to molecular structure file
            settings: xTB job settings (optional)
            index: Molecule index to use (default: "-1" for last)
            label: Job label (optional)
            jobrunner: Job runner instance (optional)
            **kwargs: Additional arguments

        Returns:
            XTBJob: Configured xTB job instance
        """
        # Read all molecules from file
        molecules = Molecule.from_filepath(
            filepath=filename, index=":", return_list=True
        )
        logger.info(f"Number of molecules read: {len(molecules)}")

        # Select specified molecule by index
        molecule = molecules[string2index_1based(index)]

        # Use default settings if not provided
        if settings is None:
            settings = XTBJobSettings.default()

        # Create jobrunner if not provided
        if jobrunner is None:
            jobrunner = JobRunner.from_job(
                cls(
                    molecule=molecule,
                    settings=settings,
                    label=label,
                    jobrunner=None,
                    **kwargs,
                ),
                server=kwargs.get("server"),
                scratch=kwargs.get("scratch"),
                fake=kwargs.get("fake", False),
                **kwargs,
            )

        # Create and return job instance
        return cls(
            molecule=molecule,
            settings=settings,
            label=label,
            jobrunner=jobrunner,
            **kwargs,
        )

    @classmethod
    def from_pubchem(
        cls, identifier, settings=None, label=None, jobrunner=None, **kwargs
    ):
        """
        Create xTB job from PubChem molecular database.

        Args:
            identifier: PubChem compound identifier (name, CID, etc.)
            settings: xTB job settings (optional)
            label: Job label (optional)
            jobrunner: Job runner instance (optional)
            **kwargs: Additional arguments

        Returns:
            XTBJob: Configured xTB job instance
        """
        # Retrieve molecule from PubChem database
        molecule = Molecule.from_pubchem(identifier=identifier)

        # Use default settings if not provided
        if settings is None:
            settings = XTBJobSettings.default()

        # Create jobrunner if not provided
        if jobrunner is None:
            jobrunner = JobRunner.from_job(
                cls(
                    molecule=molecule,
                    settings=settings,
                    label=label,
                    jobrunner=None,
                    **kwargs,
                ),
                server=kwargs.get("server"),
                scratch=kwargs.get("scratch"),
                fake=kwargs.get("fake", False),
                **kwargs,
            )

        return cls(
            molecule=molecule,
            settings=settings,
            label=label,
            jobrunner=jobrunner,
            **kwargs,
        )


class XTBSinglePointJob(XTBJob):
    """
    xTB single point energy calculation job.

    This class runs xTB single point energy calculations for a given
    molecular geometry without optimization.

    Attributes:
        TYPE (str): Job type identifier ('xtbsp').
    """

    TYPE = "xtbsp"

    def __init__(
        self, molecule, settings=None, label=None, jobrunner=None, **kwargs
    ):
        """
        Initialize xTB single point job.

        Args:
            molecule: Molecule object for the calculation
            settings: xTB job settings (optional)
            label: Job label (optional)
            jobrunner: Job runner instance (optional)
            **kwargs: Additional keyword arguments
        """
        if settings is None:
            settings = XTBJobSettings.default()
        settings.task = "sp"

        super().__init__(
            molecule=molecule,
            settings=settings,
            label=label,
            jobrunner=jobrunner,
            **kwargs,
        )


class XTBOptJob(XTBJob):
    """
    xTB geometry optimization job.

    This class runs xTB geometry optimization calculations to find
    minimum energy structures.

    Attributes:
        TYPE (str): Job type identifier ('xtbopt').
    """

    TYPE = "xtbopt"

    def __init__(
        self, molecule, settings=None, label=None, jobrunner=None, **kwargs
    ):
        """
        Initialize xTB optimization job.

        Args:
            molecule: Molecule object for the calculation
            settings: xTB job settings (optional)
            label: Job label (optional)
            jobrunner: Job runner instance (optional)
            **kwargs: Additional keyword arguments
        """
        if settings is None:
            settings = XTBJobSettings.default()
        settings.task = "opt"

        super().__init__(
            molecule=molecule,
            settings=settings,
            label=label,
            jobrunner=jobrunner,
            **kwargs,
        )
