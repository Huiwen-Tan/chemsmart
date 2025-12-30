"""
xTB output parser implementation.

This module contains the parser class for xTB output files, extracting
energies, molecular properties, geometries, frequencies, and charges.
"""

import logging
import os
import re
from functools import cached_property

import numpy as np

from chemsmart.io.molecules.structure import Molecule

logger = logging.getLogger(__name__)


class XTBOutput:
    """
    Parser for xTB semi-empirical quantum chemistry output files.

    This class provides comprehensive parsing capabilities for xTB output files,
    extracting energies, molecular properties, geometries, charges, and
    calculation statistics. xTB generates multiple output files in the
    working directory (xtbopt.xyz, charges, hessian, etc.).

    Args:
        filename (str): Path to the xTB output file
        job_folder (str): Path to the job folder containing additional output files
    """

    def __init__(self, filename, job_folder=None):
        """
        Initialize xTB output file parser.

        Args:
            filename (str): Path to the xTB output file to parse
            job_folder (str): Path to job folder for auxiliary files
        """
        self.filename = filename
        self.job_folder = (
            job_folder if job_folder else os.path.dirname(filename)
        )

        # Read file contents
        with open(self.filename) as f:
            self.contents = f.readlines()

    @cached_property
    def normal_termination(self):
        """
        Check if xTB job has completed successfully.

        Returns:
            bool: True if job terminated normally, False otherwise
        """

        def _line_contains_success_indicators(line):
            success_indicators = [
                "finished run",
                "normal termination",
            ]
            return any(
                indicator in line.lower() for indicator in success_indicators
            )

        return any(
            _line_contains_success_indicators(line)
            for line in self.contents[::-1]
        )

    @cached_property
    def energy(self):
        """
        Extract final total energy from xTB output.

        Returns:
            float or None: Total energy in Hartrees if found, None otherwise
        """
        for line in reversed(self.contents):
            if "total energy" in line.lower():
                # Match pattern like: "total energy  :      -12.34567890 Eh"
                match = re.search(r":\s+([-+]?\d+\.\d+)\s+Eh", line)
                if match:
                    return float(match.group(1))
        return None

    @cached_property
    def energies(self):
        """
        Extract all energies from optimization steps.

        Returns:
            list: List of energies for each optimization step
        """
        energies = []
        for line in self.contents:
            if "total energy" in line.lower():
                match = re.search(r":\s+([-+]?\d+\.\d+)\s+Eh", line)
                if match:
                    energies.append(float(match.group(1)))
        return energies if energies else None

    @cached_property
    def optimized_geometry(self):
        """
        Extract optimized geometry from xtbopt.xyz file.

        Returns:
            Molecule or None: Optimized molecular structure if available
        """
        xtbopt_file = os.path.join(self.job_folder, "xtbopt.xyz")
        if os.path.exists(xtbopt_file):
            try:
                return Molecule.from_filepath(xtbopt_file)
            except Exception as e:
                logger.warning(
                    f"Failed to read optimized geometry from {xtbopt_file}: {e}"
                )
                return None
        return None

    @cached_property
    def input_geometry(self):
        """
        Extract input geometry from output file.

        Returns:
            Molecule or None: Input molecular structure if available
        """
        # Look for coordinate section in output
        symbols = []
        positions = []
        reading_coords = False

        for line in self.contents:
            if "coordinates" in line.lower() or "geometry" in line.lower():
                reading_coords = True
                continue

            if reading_coords:
                parts = line.split()
                # Check if line contains atomic data (symbol and 3 coordinates)
                if len(parts) >= 4:
                    try:
                        symbol = parts[0]
                        x, y, z = map(float, parts[1:4])
                        symbols.append(symbol)
                        positions.append([x, y, z])
                    except (ValueError, IndexError):
                        if symbols:  # We've finished reading coordinates
                            break
                        continue
                elif symbols:  # Empty line after coordinates
                    break

        if symbols and positions:
            return Molecule(symbols=symbols, positions=positions)
        return None

    @cached_property
    def mulliken_charges(self):
        """
        Extract Mulliken charges from output file.

        Returns:
            list or None: List of Mulliken charges if available
        """
        charges = []
        reading_charges = False

        for line in self.contents:
            if "mulliken charges" in line.lower():
                reading_charges = True
                continue

            if reading_charges:
                # Match pattern like: "  1  C    -0.123456"
                match = re.match(
                    r"\s+\d+\s+[A-Z][a-z]?\s+([-+]?\d+\.\d+)", line
                )
                if match:
                    charges.append(float(match.group(1)))
                elif len(charges) > 0:
                    # Empty line or different section - stop reading
                    break

        return charges if charges else None

    @cached_property
    def cm5_charges(self):
        """
        Extract CM5 charges from output file.

        Returns:
            list or None: List of CM5 charges if available
        """
        charges = []
        reading_charges = False

        for line in self.contents:
            if "cm5 charges" in line.lower():
                reading_charges = True
                continue

            if reading_charges:
                match = re.match(
                    r"\s+\d+\s+[A-Z][a-z]?\s+([-+]?\d+\.\d+)", line
                )
                if match:
                    charges.append(float(match.group(1)))
                elif len(charges) > 0:
                    break

        return charges if charges else None

    @cached_property
    def charges_from_file(self):
        """
        Read charges from the 'charges' file.

        xTB writes charges to a separate file named 'charges'.

        Returns:
            list or None: List of charges if file exists
        """
        charges_file = os.path.join(self.job_folder, "charges")
        if os.path.exists(charges_file):
            try:
                charges = []
                with open(charges_file) as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 1:
                            try:
                                charges.append(float(parts[0]))
                            except ValueError:
                                continue
                return charges if charges else None
            except Exception as e:
                logger.warning(f"Failed to read charges file: {e}")
                return None
        return None

    @cached_property
    def frequencies(self):
        """
        Extract vibrational frequencies from output.

        Returns:
            list or None: List of frequencies in cm^-1 if available
        """
        frequencies = []
        reading_freq = False

        for line in self.contents:
            if "frequencies" in line.lower() or "vibspectrum" in line.lower():
                reading_freq = True
                continue

            if reading_freq:
                # Match frequency patterns
                match = re.search(r"(\d+\.\d+)\s*cm", line)
                if match:
                    frequencies.append(float(match.group(1)))
                elif frequencies and (
                    "---" in line or len(line.strip()) == 0
                ):
                    # End of frequency section
                    break

        return frequencies if frequencies else None

    @cached_property
    def has_imaginary_frequency(self):
        """
        Check if calculation has imaginary frequencies.

        Returns:
            bool: True if imaginary frequencies are present
        """
        for line in self.contents:
            if "imaginary" in line.lower() and "frequency" in line.lower():
                return True
        return False

    @cached_property
    def dipole_moment(self):
        """
        Extract dipole moment from output.

        Returns:
            float or None: Dipole moment in Debye if available
        """
        for line in self.contents:
            if "dipole moment" in line.lower():
                # Match pattern for dipole moment value
                match = re.search(r":\s+([-+]?\d+\.\d+)", line)
                if match:
                    return float(match.group(1))
        return None

    @cached_property
    def num_atoms(self):
        """
        Extract number of atoms from output.

        Returns:
            int or None: Number of atoms if found
        """
        for line in self.contents:
            if "# atoms" in line.lower():
                match = re.search(r":\s*(\d+)", line)
                if match:
                    return int(match.group(1))
        return None

    @cached_property
    def charge(self):
        """
        Extract molecular charge from output.

        Returns:
            int or None: Molecular charge if found
        """
        for line in self.contents:
            if line.strip().startswith("charge"):
                match = re.search(r":\s*([-+]?\d+)", line)
                if match:
                    return int(match.group(1))
        return None

    @cached_property
    def multiplicity(self):
        """
        Extract spin multiplicity from output.

        xTB reports unpaired electrons, so multiplicity = unpaired + 1.

        Returns:
            int or None: Spin multiplicity if found
        """
        for line in self.contents:
            if "unpaired" in line.lower():
                match = re.search(r":\s*(\d+)", line)
                if match:
                    unpaired = int(match.group(1))
                    return unpaired + 1
        return None

    @cached_property
    def optimization_converged(self):
        """
        Check if geometry optimization converged.

        Returns:
            bool: True if optimization converged
        """
        for line in self.contents:
            if "optimization converged" in line.lower():
                return True
        return False

    @cached_property
    def wall_time(self):
        """
        Extract wall time from output.

        Returns:
            str or None: Wall time string if found
        """
        for line in reversed(self.contents):
            if "wall-time" in line.lower():
                # Extract time information
                return line.split(":")[-1].strip()
        return None

    def get_all_properties(self):
        """
        Get a dictionary of all parsed properties.

        Returns:
            dict: Dictionary containing all available properties
        """
        return {
            "normal_termination": self.normal_termination,
            "energy": self.energy,
            "energies": self.energies,
            "optimized_geometry": self.optimized_geometry,
            "input_geometry": self.input_geometry,
            "mulliken_charges": self.mulliken_charges,
            "cm5_charges": self.cm5_charges,
            "charges_from_file": self.charges_from_file,
            "frequencies": self.frequencies,
            "has_imaginary_frequency": self.has_imaginary_frequency,
            "dipole_moment": self.dipole_moment,
            "num_atoms": self.num_atoms,
            "charge": self.charge,
            "multiplicity": self.multiplicity,
            "optimization_converged": self.optimization_converged,
            "wall_time": self.wall_time,
        }
