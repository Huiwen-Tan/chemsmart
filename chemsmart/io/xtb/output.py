"""
xTB output parser implementation.

This module contains parsers for xTB output files to extract
energies, geometries, frequencies, and other properties.
"""

import logging
import os
import re
from functools import cached_property

import ase.io
import numpy as np

from chemsmart.io.molecules.structure import Molecule

logger = logging.getLogger(__name__)


class XTBOutput:
    """
    Parser for xTB output files.

    This class provides comprehensive parsing capabilities for xTB output files,
    extracting energies, molecular properties, geometries, frequencies, and
    charges from xTB calculations.

    Args:
        filename (str): Path to the xTB output file
        job_folder (str, optional): Path to job folder containing auxiliary files
    """

    def __init__(self, filename, job_folder=None):
        """
        Initialize xTB output file parser.

        Args:
            filename: Path to the xTB output file to parse
            job_folder: Path to folder containing additional output files
        """
        self.filename = filename
        self.job_folder = job_folder or os.path.dirname(filename)

        # Read file contents
        with open(self.filename, "r") as f:
            self.contents = f.readlines()

    @cached_property
    def normal_termination(self):
        """
        Check if xTB job has completed successfully.

        Returns:
            bool: True if job terminated normally, False otherwise
        """
        # Check for successful termination indicators
        success_indicators = [
            "normal termination of xtb",
            "finished run",
        ]

        for line in self.contents[::-1]:  # Check from end of file
            line_lower = line.lower()
            if any(indicator in line_lower for indicator in success_indicators):
                return True

        return False

    @cached_property
    def energy(self):
        """
        Extract the final total energy from xTB output.

        Returns:
            float or None: Total energy in Hartree, or None if not found
        """
        energies = self.energies
        if energies:
            return energies[-1]
        return None

    @cached_property
    def energies(self):
        """
        Extract all energies from xTB output (for optimization steps).

        Returns:
            list: List of energies in Hartree
        """
        energies = []

        # Pattern for total energy in xTB output
        # Example: "          | TOTAL ENERGY              -10.123456789012 Eh   |"
        # Handle both regular floats and scientific notation
        energy_pattern = re.compile(
            r"TOTAL ENERGY\s+([-+]?\d+\.\d+(?:[eE][-+]?\d+)?)\s+Eh"
        )

        for line in self.contents:
            match = energy_pattern.search(line)
            if match:
                energy = float(match.group(1))
                energies.append(energy)

        return energies

    @cached_property
    def optimized_structure(self):
        """
        Extract optimized molecular structure.

        For optimization jobs, reads from xtbopt.xyz file.
        For single point jobs, returns input structure.

        Returns:
            Molecule or None: Optimized molecular structure
        """
        # Check for xtbopt.xyz file (optimization output)
        xtbopt_file = os.path.join(self.job_folder, "xtbopt.xyz")

        if os.path.exists(xtbopt_file):
            try:
                atoms = ase.io.read(xtbopt_file)
                molecule = Molecule.from_ase_atoms(atoms)
                logger.info(f"Read optimized structure from {xtbopt_file}")
                return molecule
            except Exception as e:
                logger.error(f"Failed to read optimized structure: {e}")
                return None

        # If no optimization file, try to extract from main output
        return self._extract_structure_from_output()

    def _extract_structure_from_output(self):
        """
        Extract molecular structure from main output file.

        Returns:
            Molecule or None: Molecular structure
        """
        # xTB prints coordinates in various places
        # Look for final coordinates section
        coord_section = False
        coordinates = []

        for i, line in enumerate(self.contents):
            if "final structure" in line.lower():
                coord_section = True
                continue

            if coord_section:
                # Parse coordinate lines
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        symbol = parts[0]
                        x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                        coordinates.append((symbol, [x, y, z]))
                    except (ValueError, IndexError):
                        # End of coordinates section
                        if coordinates:
                            break

        if coordinates:
            try:
                symbols = [coord[0] for coord in coordinates]
                positions = [coord[1] for coord in coordinates]
                atoms = ase.Atoms(symbols=symbols, positions=positions)
                return Molecule.from_ase_atoms(atoms)
            except Exception as e:
                logger.error(f"Failed to create molecule from coordinates: {e}")

        return None

    @cached_property
    def all_structures(self):
        """
        Extract all optimization geometries.

        Returns:
            list: List of Molecule objects for each optimization step
        """
        # For now, return just the final structure
        # Full trajectory parsing could be added later
        if self.optimized_structure:
            return [self.optimized_structure]
        return []

    @cached_property
    def frequencies(self):
        """
        Extract vibrational frequencies from frequency calculation.

        Returns:
            list or None: List of frequencies in cm^-1, or None if not available
        """
        frequencies = []

        # Pattern for frequencies in xTB output
        freq_pattern = re.compile(r"^\s*\d+\s+([-+]?\d+\.\d+)\s+cm\*\*-1")

        in_freq_section = False
        for line in self.contents:
            if "mode" in line.lower() and "cm**-1" in line.lower():
                in_freq_section = True
                continue

            if in_freq_section:
                match = freq_pattern.search(line)
                if match:
                    freq = float(match.group(1))
                    frequencies.append(freq)
                elif line.strip() == "":
                    # End of frequency section
                    break

        return frequencies if frequencies else None

    @cached_property
    def charges(self):
        """
        Extract atomic charges.

        Returns:
            dict or None: Dictionary with charge types and arrays
        """
        charges_data = {}

        # Check for charges file
        charges_file = os.path.join(self.job_folder, "charges")
        if os.path.exists(charges_file):
            try:
                with open(charges_file, "r") as f:
                    charge_lines = f.readlines()

                charges_array = []
                for line in charge_lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            charge = float(parts[1])
                            charges_array.append(charge)
                        except ValueError:
                            continue

                if charges_array:
                    charges_data["charges"] = np.array(charges_array)
            except Exception as e:
                logger.warning(f"Failed to read charges file: {e}")

        # Parse charges from main output
        mulliken_charges = self._extract_mulliken_charges()
        if mulliken_charges is not None:
            charges_data["mulliken"] = mulliken_charges

        cm5_charges = self._extract_cm5_charges()
        if cm5_charges is not None:
            charges_data["cm5"] = cm5_charges

        return charges_data if charges_data else None

    def _extract_mulliken_charges(self):
        """
        Extract Mulliken charges from output.

        Returns:
            np.ndarray or None: Array of Mulliken charges
        """
        charges = []
        in_mulliken_section = False

        for line in self.contents:
            if "Mulliken" in line and "charges" in line:
                in_mulliken_section = True
                continue

            if in_mulliken_section:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        # Format: atom_number symbol charge
                        charge = float(parts[2])
                        charges.append(charge)
                    except (ValueError, IndexError):
                        # End of section
                        if charges:
                            break

        return np.array(charges) if charges else None

    def _extract_cm5_charges(self):
        """
        Extract CM5 charges from output.

        Returns:
            np.ndarray or None: Array of CM5 charges
        """
        charges = []
        in_cm5_section = False

        for line in self.contents:
            if "CM5" in line and "charges" in line:
                in_cm5_section = True
                continue

            if in_cm5_section:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        charge = float(parts[2])
                        charges.append(charge)
                    except (ValueError, IndexError):
                        if charges:
                            break

        return np.array(charges) if charges else None

    @cached_property
    def dipole_moment(self):
        """
        Extract dipole moment.

        Returns:
            dict or None: Dictionary with dipole components and magnitude
        """
        # Pattern for dipole moment in xTB output
        for idx, line in enumerate(self.contents):
            if "molecular dipole" in line.lower():
                # Next few lines contain dipole information
                for i in range(idx, min(idx + 10, len(self.contents))):
                    if "total (Debye)" in self.contents[i]:
                        parts = self.contents[i].split()
                        try:
                            magnitude = float(parts[-1])
                            return {"magnitude": magnitude, "unit": "Debye"}
                        except (ValueError, IndexError):
                            pass

        return None

    def __repr__(self):
        """String representation of output."""
        status = "complete" if self.normal_termination else "incomplete"
        energy_str = f"{self.energy:.6f} Eh" if self.energy else "N/A"
        return f"XTBOutput(status={status}, energy={energy_str})"
