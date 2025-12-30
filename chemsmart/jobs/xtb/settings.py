"""
xTB job settings implementation.

This module contains the settings classes for configuring xTB semi-empirical
quantum chemistry calculations, including general settings and specialized
settings for different calculation types.
"""

import copy
import logging
import os

from chemsmart.jobs.settings import MolecularJobSettings

logger = logging.getLogger(__name__)


class XTBJobSettings(MolecularJobSettings):
    """
    Settings for xTB semi-empirical quantum chemistry jobs.

    This class handles the configuration of xTB calculations including
    method selection (GFN0-xTB, GFN1-xTB, GFN2-xTB, GFN-FF), calculation types,
    solvation, and various computational parameters.

    xTB is command-line driven, so settings are converted to command-line
    arguments rather than input file content.

    Attributes:
        method (str | None): xTB method (e.g., 'GFN2-xTB', 'GFN1-xTB', 'GFN0-xTB', 'GFN-FF').
        charge (int | None): Molecular charge.
        multiplicity (int | None): Spin multiplicity (uhf parameter in xTB).
        solvent_model (str | None): Solvation model identifier ('gbsa' or 'alpb').
        solvent_id (str | None): Solvent identifier (e.g., 'water', 'methanol').
        job_type (str | None): Calculation type (e.g., 'opt', 'sp', 'freq').
        optimization_level (str | None): Optimization level ('crude', 'sloppy', 'loose',
            'lax', 'normal', 'tight', 'vtight', 'extreme').
        max_iterations (int | None): Maximum optimization iterations.
        accuracy (float | None): Numerical accuracy for SCF (default: 1.0).
        electronic_temp (float | None): Electronic temperature in Kelvin.
        parallel (int | None): Number of parallel threads.
        additional_options (str | None): Additional command-line options.
    """

    def __init__(
        self,
        method=None,
        charge=None,
        multiplicity=None,
        solvent_model=None,
        solvent_id=None,
        job_type=None,
        optimization_level=None,
        max_iterations=None,
        accuracy=None,
        electronic_temp=None,
        parallel=None,
        additional_options=None,
        **kwargs,
    ):
        """
        Initialize xTB job settings.

        Args:
            method: xTB method (e.g., 'GFN2-xTB', 'GFN1-xTB')
            charge: Molecular charge
            multiplicity: Spin multiplicity
            solvent_model: Solvation model ('gbsa' or 'alpb')
            solvent_id: Solvent identifier
            job_type: Type of calculation ('sp', 'opt', 'freq')
            optimization_level: Optimization convergence level
            max_iterations: Maximum optimization iterations
            accuracy: Numerical accuracy for SCF
            electronic_temp: Electronic temperature in Kelvin
            parallel: Number of parallel threads
            additional_options: Additional command-line options
            **kwargs: Additional keyword arguments
        """
        super().__init__(
            charge=charge,
            multiplicity=multiplicity,
            job_type=job_type,
            solvent_model=solvent_model,
            solvent_id=solvent_id,
            **kwargs,
        )

        # xTB-specific parameters
        self.method = method if method is not None else "GFN2-xTB"
        self.optimization_level = optimization_level
        self.max_iterations = max_iterations
        self.accuracy = accuracy
        self.electronic_temp = electronic_temp
        self.parallel = parallel
        self.additional_options = additional_options

        # Validate method
        valid_methods = ["GFN0-xTB", "GFN1-xTB", "GFN2-xTB", "GFN-FF"]
        if self.method not in valid_methods:
            logger.warning(
                f"Method {self.method} may not be a standard xTB method. "
                f"Valid methods are: {valid_methods}"
            )

    def merge(
        self, other, keywords=("charge", "multiplicity"), merge_all=False
    ):
        """
        Merge this settings object with another.

        Args:
            other: Settings object or dictionary to merge with
            keywords: Specific keywords to merge if merge_all is False
            merge_all: Whether to merge all attributes

        Returns:
            XTBJobSettings: New merged settings object
        """

        other_dict = other if isinstance(other, dict) else other.__dict__

        if merge_all:
            # Update self with other for all
            merged_dict = self.__dict__.copy()
            merged_dict.update(other_dict)
            return type(self)(**merged_dict)

        if keywords is not None:
            other_dict = {
                k: other_dict[k] for k in keywords if k in other_dict
            }
        # Update self with other
        merged_dict = self.__dict__.copy()
        merged_dict.update(other_dict)
        return type(self)(**merged_dict)

    def copy(self):
        """
        Create a deep copy of the settings object.

        Returns:
            XTBJobSettings: Deep copy of this settings object
        """
        return copy.deepcopy(self)

    def __getitem__(self, key):
        """
        Get settings attribute by key.

        Args:
            key: Attribute name to retrieve

        Returns:
            Value of the specified attribute
        """
        return self.__dict__[key]

    def __eq__(self, other):
        """
        Check equality with another settings object.

        Args:
            other: Another settings object to compare

        Returns:
            bool: True if settings are equal, False otherwise
        """
        if type(self) is not type(other):
            return NotImplemented

        return self.__dict__ == other.__dict__

    @classmethod
    def from_xyzfile(cls):
        """
        Create default xTB job settings for .xyz file input.

        Returns:
            XTBJobSettings: Default xTB settings for xyz input
        """
        return XTBJobSettings.default()

    @classmethod
    def from_filepath(cls, filepath, **kwargs):
        """
        Create settings from any supported file type.

        Args:
            filepath: Path to the input file
            **kwargs: Additional keyword arguments

        Returns:
            XTBJobSettings or None: Settings object if file type supported
        """

        if ".xyz" in filepath:
            return cls.from_xyzfile()

        return None

    @classmethod
    def default(cls):
        """
        Create default xTB job settings.

        Returns:
            XTBJobSettings: Default settings object with GFN2-xTB method
        """
        return cls(
            method="GFN2-xTB",
            charge=0,
            multiplicity=1,
            solvent_model=None,
            solvent_id=None,
            job_type="sp",
            optimization_level=None,
            max_iterations=None,
            accuracy=None,
            electronic_temp=None,
            parallel=None,
            additional_options=None,
        )

    def get_command_args(self):
        """
        Generate xTB command-line arguments from settings.

        Returns:
            list: List of command-line arguments for xTB
        """
        args = []

        # Add job type
        if self.job_type == "opt":
            args.append("--opt")
            if self.optimization_level is not None:
                args.append(self.optimization_level)
        elif self.job_type == "freq":
            args.append("--hess")

        # Add method (GFN parameter)
        if self.method == "GFN2-xTB":
            args.extend(["--gfn", "2"])
        elif self.method == "GFN1-xTB":
            args.extend(["--gfn", "1"])
        elif self.method == "GFN0-xTB":
            args.extend(["--gfn", "0"])
        elif self.method == "GFN-FF":
            args.extend(["--gfnff"])

        # Add charge
        if self.charge is not None and self.charge != 0:
            args.extend(["--chrg", str(self.charge)])

        # Add multiplicity (unpaired electrons for xTB)
        if self.multiplicity is not None and self.multiplicity != 1:
            # xTB uses uhf parameter for unpaired electrons
            unpaired = self.multiplicity - 1
            args.extend(["--uhf", str(unpaired)])

        # Add solvation
        if self.solvent_model is not None and self.solvent_id is not None:
            if self.solvent_model.lower() == "gbsa":
                args.extend(["--gbsa", self.solvent_id])
            elif self.solvent_model.lower() == "alpb":
                args.extend(["--alpb", self.solvent_id])

        # Add accuracy
        if self.accuracy is not None:
            args.extend(["--acc", str(self.accuracy)])

        # Add electronic temperature
        if self.electronic_temp is not None:
            args.extend(["--etemp", str(self.electronic_temp)])

        # Add parallel
        if self.parallel is not None:
            args.extend(["--parallel", str(self.parallel)])

        # Add max iterations
        if self.max_iterations is not None:
            args.extend(["--iterations", str(self.max_iterations)])

        # Add additional options
        if self.additional_options is not None:
            # Split additional options and add them
            args.extend(self.additional_options.split())

        return args
