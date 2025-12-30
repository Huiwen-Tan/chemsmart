"""
xTB input writer implementation.

This module contains the writer class for xTB input files.
Unlike Gaussian/ORCA, xTB primarily uses XYZ files as input and
command-line arguments for settings.
"""

import logging
import os

logger = logging.getLogger(__name__)


class XTBInputWriter:
    """
    Writer for xTB input files.

    xTB uses simple XYZ coordinate files as input. Settings are
    passed via command-line arguments rather than input file content.

    Attributes:
        job: XTB job object containing molecule and settings.
    """

    def __init__(self, job):
        """
        Initialize xTB input writer.

        Args:
            job: XTB job object
        """
        self.job = job

    def write(self, target_directory=None):
        """
        Write xTB input file (XYZ format).

        Args:
            target_directory: Directory to write the file to (optional)
        """
        if target_directory is None:
            target_directory = self.job.folder

        # Ensure target directory exists
        os.makedirs(target_directory, exist_ok=True)

        # Write XYZ file
        xyz_file = os.path.join(target_directory, f"{self.job.label}.xyz")

        with open(xyz_file, "w") as f:
            # Write XYZ format
            num_atoms = len(self.job.molecule)
            f.write(f"{num_atoms}\n")

            # Write comment line (can include label or other info)
            f.write(f"{self.job.label}\n")

            # Write coordinates
            for symbol, position in zip(
                self.job.molecule.chemical_symbols,
                self.job.molecule.positions,
                strict=False,
            ):
                x, y, z = position
                f.write(f"{symbol:5} {x:15.10f} {y:15.10f} {z:15.10f}\n")

        logger.info(f"Written xTB input file: {xyz_file}")
