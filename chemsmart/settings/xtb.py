"""
xTB job settings implementation.

This module contains the settings classes for configuring xTB
semi-empirical quantum chemistry calculations.
"""

import copy
import logging

logger = logging.getLogger(__name__)


class XTBJobSettings:
    """
    Settings for xTB quantum chemistry jobs.

    This class handles the configuration of xTB calculations including
    method selection (GFN0, GFN1, GFN2, GFN-FF), task types, and
    various xTB-specific options.

    Attributes:
        method (str): xTB method to use ('GFN0-xTB', 'GFN1-xTB', 'GFN2-xTB', 'GFN-FF').
        charge (int): Molecular charge.
        multiplicity (int): Spin multiplicity (unpaired electrons + 1).
        solvent (str | None): Solvent for ALPB implicit solvation.
        task (str): Task type ('sp', 'opt', 'hess', 'ohess', 'md', 'metadyn', 'path').
        accuracy (float | None): Numerical accuracy (default varies by task).
        electronic_temp (float | None): Electronic temperature in K.
        max_iterations (int | None): Maximum SCF iterations.
        opt_level (str | None): Optimization level ('crude', 'sloppy', 'loose', 'normal', 'tight', 'vtight', 'extreme').
        parallel (int | None): Number of parallel threads for SMP parallelization.
        additional_input (str | None): Additional xTB input directives.
    """

    def __init__(
        self,
        method="GFN2-xTB",
        charge=0,
        multiplicity=1,
        solvent=None,
        task="sp",
        accuracy=None,
        electronic_temp=None,
        max_iterations=None,
        opt_level=None,
        parallel=None,
        additional_input=None,
        **kwargs,
    ):
        """
        Initialize xTB job settings.

        Args:
            method: xTB method ('GFN0-xTB', 'GFN1-xTB', 'GFN2-xTB', 'GFN-FF')
            charge: Molecular charge
            multiplicity: Spin multiplicity
            solvent: Solvent identifier for ALPB solvation
            task: Task type ('sp', 'opt', 'hess', 'ohess', 'md', 'metadyn', 'path')
            accuracy: Numerical accuracy
            electronic_temp: Electronic temperature in Kelvin
            max_iterations: Maximum SCF iterations
            opt_level: Optimization convergence level
            parallel: Number of parallel threads
            additional_input: Additional xTB directives
            **kwargs: Additional keyword arguments
        """
        self.method = method
        self.charge = charge
        self.multiplicity = multiplicity
        self.solvent = solvent
        self.task = task
        self.accuracy = accuracy
        self.electronic_temp = electronic_temp
        self.max_iterations = max_iterations
        self.opt_level = opt_level
        self.parallel = parallel
        self.additional_input = additional_input

        # Store any additional kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_method_flag(self):
        """
        Get the xTB method command-line flag.

        Returns:
            str: Method flag for xTB command line
        """
        method_map = {
            "GFN0-xTB": "--gfn 0",
            "GFN1-xTB": "--gfn 1",
            "GFN2-xTB": "--gfn 2",
            "GFN-FF": "--gfnff",
        }
        return method_map.get(self.method, "--gfn 2")

    def get_task_flag(self):
        """
        Get the xTB task command-line flag.

        Returns:
            str: Task flag for xTB command line
        """
        task_map = {
            "sp": "",  # Single point (no flag needed)
            "opt": "--opt",
            "hess": "--hess",
            "ohess": "--ohess",  # Optimization + frequency
            "md": "--md",
            "metadyn": "--metadyn",
            "path": "--path",
        }
        return task_map.get(self.task, "")

    def build_command_args(self, input_file):
        """
        Build the complete xTB command-line arguments.

        Args:
            input_file: Path to input geometry file (typically .xyz)

        Returns:
            list: List of command-line arguments for xTB
        """
        args = [input_file]

        # Add task flag
        task_flag = self.get_task_flag()
        if task_flag:
            args.append(task_flag)

        # Add method flag
        method_flag = self.get_method_flag()
        if method_flag:
            args.extend(method_flag.split())

        # Add charge
        args.extend(["--chrg", str(self.charge)])

        # Add unpaired electrons (multiplicity - 1)
        unpaired = self.multiplicity - 1
        if unpaired > 0:
            args.extend(["--uhf", str(unpaired)])

        # Add solvent if specified
        if self.solvent:
            args.extend(["--alpb", self.solvent])

        # Add accuracy if specified
        if self.accuracy is not None:
            args.extend(["--acc", str(self.accuracy)])

        # Add electronic temperature if specified
        if self.electronic_temp is not None:
            args.extend(["--etemp", str(self.electronic_temp)])

        # Add max iterations if specified
        if self.max_iterations is not None:
            args.extend(["--iterations", str(self.max_iterations)])

        # Add optimization level if specified
        if self.opt_level is not None:
            args.extend(["--" + self.opt_level])

        # Add parallel threads if specified
        if self.parallel is not None:
            args.extend(["--parallel", str(self.parallel)])

        return args

    def copy(self):
        """
        Create a deep copy of the settings object.

        Returns:
            XTBJobSettings: Deep copy of this settings object
        """
        return copy.deepcopy(self)

    def merge(self, other, merge_all=False):
        """
        Merge this settings object with another.

        Args:
            other: Settings object or dictionary to merge with
            merge_all: Whether to merge all attributes

        Returns:
            XTBJobSettings: New merged settings object
        """
        other_dict = other if isinstance(other, dict) else other.__dict__

        if merge_all:
            merged_dict = self.__dict__.copy()
            merged_dict.update(other_dict)
            return type(self)(**merged_dict)

        # Only update non-None values from other
        merged_dict = self.__dict__.copy()
        for key, value in other_dict.items():
            if value is not None:
                merged_dict[key] = value
        return type(self)(**merged_dict)

    @classmethod
    def default(cls):
        """
        Create default xTB job settings.

        Returns:
            XTBJobSettings: Default settings object
        """
        return cls(
            method="GFN2-xTB",
            charge=0,
            multiplicity=1,
            solvent=None,
            task="sp",
            accuracy=None,
            electronic_temp=None,
            max_iterations=None,
            opt_level=None,
            parallel=None,
            additional_input=None,
        )

    def __repr__(self):
        """String representation of settings."""
        return f"XTBJobSettings(method={self.method}, task={self.task}, charge={self.charge}, multiplicity={self.multiplicity})"

    def __eq__(self, other):
        """Check equality with another settings object."""
        if type(self) is not type(other):
            return NotImplemented
        return self.__dict__ == other.__dict__
