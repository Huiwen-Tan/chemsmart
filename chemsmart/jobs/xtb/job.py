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
from chemsmart.jobs.xtb.settings import XTBJobSettings
from chemsmart.utils.utils import string2index_1based

logger = logging.getLogger(__name__)


class XTBJob(Job):
    """
    Base xTB job class.

    This class provides the foundation for all xTB semi-empirical quantum
    chemistry calculations including setup, execution, and output handling.

    xTB is command-line driven rather than input-file driven, and generates
    multiple output files in the working directory.

    Attributes:
        PROGRAM (str): Program identifier ('xtb').
        molecule (Molecule): Molecular structure used for the calculation.
        settings (XTBJobSettings): Configuration options for the job.
        label (str): Job identifier used for file naming.
        jobrunner (JobRunner): Execution backend that runs the job.
        skip_completed (bool): If True, completed jobs are not rerun.
    """

    PROGRAM = "xtb"

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
        self.settings = (
            settings.copy() if settings is not None else XTBJobSettings.default()
        )

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
        Get the input file path for the xTB job (XYZ file).

        Returns:
            str: Absolute path to the input XYZ file
        """
        inputfile = self.label + ".xyz"
        return os.path.join(self.folder, inputfile)

    @property
    def outputfile(self):
        """
        Get the output file path for the xTB job.

        xTB writes to a file typically named based on the input or to stdout.

        Returns:
            str: Absolute path to the output file
        """
        outputfile = self.label + ".out"
        return os.path.join(self.folder, outputfile)

    @property
    def xtbopt_file(self):
        """
        Get the optimized geometry file path (xtbopt.xyz).

        Returns:
            str: Absolute path to the optimized geometry file
        """
        return os.path.join(self.folder, "xtbopt.xyz")

    @property
    def xtbhess_file(self):
        """
        Get the Hessian file path (hessian).

        Returns:
            str: Absolute path to the Hessian file
        """
        return os.path.join(self.folder, "hessian")

    @property
    def charges_file(self):
        """
        Get the charges file path (charges).

        Returns:
            str: Absolute path to the charges file
        """
        return os.path.join(self.folder, "charges")

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

        # Backup xTB-specific output files if they exist
        if os.path.exists(self.xtbopt_file):
            self.backup_file(self.xtbopt_file, folder=folder, **kwargs)
        if os.path.exists(self.xtbhess_file):
            self.backup_file(self.xtbhess_file, folder=folder, **kwargs)
        if os.path.exists(self.charges_file):
            self.backup_file(self.charges_file, folder=folder, **kwargs)

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
        except AttributeError as e:
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
        keywords=("charge", "multiplicity"),
        **kwargs,
    ):
        """
        Create xTB job from molecular structure file.

        This factory method reads molecular structures from various file
        formats and creates an xTB job with appropriate settings.

        Args:
            filename: Path to molecular structure file
            settings: xTB job settings (optional)
            index: Molecule index to use (default: "-1" for last)
            label: Job label (optional)
            jobrunner: Job runner instance (optional)
            keywords: Settings keywords to use
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
        molecules = molecules[string2index_1based(index)]

        # Create default settings if not provided
        if settings is None:
            settings = XTBJobSettings.default()

        # Create jobrunner if not provided
        if jobrunner is None:
            jobrunner = JobRunner.from_job(
                cls(
                    molecule=molecules,
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
            molecule=molecules,
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

        This factory method retrieves molecular structures from PubChem
        database and creates an xTB job for quantum chemistry calculations.

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

        # Create default settings if not provided
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


class XTBGeneralJob(XTBJob):
    """
    General xTB job implementation.

    This class provides a general xTB job implementation that subclasses
    XTBJob. It prevents recursive loops in specialized xTB job classes
    that need to create and run general xTB jobs internally.

    Attributes:
        TYPE (str): Job type identifier ('xtbjob').
        molecule (Molecule): Molecular structure used for the calculation.
        settings (XTBJobSettings): Configuration options for the job.
        label (str): Job identifier used for file naming.
        jobrunner (JobRunner): Execution backend that runs the job.
        skip_completed (bool): If True, completed jobs are not rerun.
    """

    TYPE = "xtbjob"

    def __init__(self, molecule, settings=None, label=None, **kwargs):
        """
        Initialize general xTB job.

        Args:
            molecule: Molecule object for the calculation
            settings: xTB job settings (optional)
            label: Job label (optional)
            **kwargs: Additional keyword arguments
        """
        super().__init__(
            molecule=molecule, settings=settings, label=label, **kwargs
        )
