#!/usr/bin/env python
"""
Frontier Molecular Orbital (FMO) analysis script.

This script extracts and analyzes Frontier Molecular Orbital data from
Gaussian and ORCA output files, supporting both closed-shell and open-shell
(radical) systems.
"""

import logging
import os

import click

from chemsmart.io.gaussian.output import Gaussian16Output
from chemsmart.io.orca.output import ORCAOutput
from chemsmart.utils.io import get_outfile_format
from chemsmart.utils.logger import create_logger

logger = logging.getLogger(__name__)
os.environ["OMP_NUM_THREADS"] = "1"

# Conversion factor from eV to kcal/mol
EV_TO_KCAL_MOL = 23.06054195


def _apply_unit_conversion(value, unit):
    """Apply unit conversion if needed."""
    if value is None:
        return None
    if unit.lower() == "kcal/mol":
        return value * EV_TO_KCAL_MOL
    return value


def _display_closed_shell_fmo(outputfile, unit, energy_unit):
    """Display FMO properties for closed-shell systems."""
    homo_energy = _apply_unit_conversion(outputfile.homo_energy, unit)
    lumo_energy = _apply_unit_conversion(outputfile.lumo_energy, unit)
    fmo_gap = _apply_unit_conversion(outputfile.fmo_gap, unit)

    # obtain chemical potential, μ = 1/2 * (lumo_energy + homo_energy)
    # Chemical hardness, η = 1/2 * (lumo_energy - homo_energy)
    # Electrophilicity index = ω = μ^2/2η
    chemical_potential = 1 / 2 * (lumo_energy + homo_energy)
    chemical_hardness = 1 / 2 * (lumo_energy - homo_energy)
    electrophilicity_index = chemical_potential**2 / (2 * chemical_hardness)

    logger.info(f"HOMO energy: {homo_energy:.4f} {energy_unit}")
    logger.info(f"LUMO energy: {lumo_energy:.4f} {energy_unit}")
    logger.info(f"HOMO-LUMO gap: {fmo_gap:.4f} {energy_unit}")
    logger.info(
        f"Chemical potential, mu: {chemical_potential:.4} {energy_unit}"
    )
    logger.info(
        f"Chemical hardness, eta: {chemical_hardness:.4} {energy_unit}"
    )
    logger.info(
        f"Electrophilicity Index, omega: {electrophilicity_index:.4} "
        f"{energy_unit}"
    )


def _display_open_shell_fmo(outputfile, unit, energy_unit):
    """Display FMO properties for open-shell (radical) systems."""
    multiplicity = outputfile.multiplicity
    num_unpaired = outputfile.num_unpaired_electrons

    logger.info("=" * 50)
    logger.info("Open-shell system detected")
    logger.info(f"Multiplicity: {multiplicity}")
    logger.info(f"Number of unpaired electrons: {num_unpaired}")
    logger.info("=" * 50)

    # Display SOMO energies
    somo_energies = outputfile.somo_energies
    if somo_energies:
        logger.info(f"Number of SOMOs: {len(somo_energies)}")
        for i, somo_e in enumerate(somo_energies, 1):
            somo_e_converted = _apply_unit_conversion(somo_e, unit)
            logger.info(f"SOMO {i} energy: {somo_e_converted:.4f} {energy_unit}")

        lowest_somo = _apply_unit_conversion(
            outputfile.lowest_somo_energy, unit
        )
        highest_somo = _apply_unit_conversion(
            outputfile.highest_somo_energy, unit
        )
        logger.info(f"Lowest SOMO energy: {lowest_somo:.4f} {energy_unit}")
        logger.info(f"Highest SOMO energy: {highest_somo:.4f} {energy_unit}")

    # Display alpha and beta orbital energies
    logger.info("-" * 50)
    logger.info("Alpha spin channel:")
    homo_alpha = _apply_unit_conversion(outputfile.homo_alpha_energy, unit)
    lumo_alpha = _apply_unit_conversion(outputfile.lumo_alpha_energy, unit)
    if homo_alpha is not None:
        logger.info(f"  HOMO(alpha) energy: {homo_alpha:.4f} {energy_unit}")
    if lumo_alpha is not None:
        logger.info(f"  LUMO(alpha) energy: {lumo_alpha:.4f} {energy_unit}")

    logger.info("Beta spin channel:")
    homo_beta = _apply_unit_conversion(outputfile.homo_beta_energy, unit)
    lumo_beta = _apply_unit_conversion(outputfile.lumo_beta_energy, unit)
    if homo_beta is not None:
        logger.info(f"  HOMO(beta) energy: {homo_beta:.4f} {energy_unit}")
    if lumo_beta is not None:
        logger.info(f"  LUMO(beta) energy: {lumo_beta:.4f} {energy_unit}")

    # Display FMO gap (calculated as min(LUMO_alpha, LUMO_beta) - HOMO_alpha)
    fmo_gap = _apply_unit_conversion(outputfile.fmo_gap, unit)
    logger.info("-" * 50)
    logger.info(f"FMO gap (SOMO-LUMO): {fmo_gap:.4f} {energy_unit}")

    # Calculate chemical properties using effective HOMO/LUMO
    # For open-shell: effective HOMO = highest SOMO (homo_alpha)
    # For open-shell: effective LUMO = min(lumo_alpha, lumo_beta)
    effective_homo = _apply_unit_conversion(
        outputfile.highest_somo_energy, unit
    )

    lumo_alpha = outputfile.lumo_alpha_energy
    lumo_beta = outputfile.lumo_beta_energy

    # Handle case where one or both LUMO energies might be None
    if lumo_alpha is not None and lumo_beta is not None:
        effective_lumo = _apply_unit_conversion(
            min(lumo_alpha, lumo_beta), unit
        )
    elif lumo_alpha is not None:
        effective_lumo = _apply_unit_conversion(lumo_alpha, unit)
    elif lumo_beta is not None:
        effective_lumo = _apply_unit_conversion(lumo_beta, unit)
    else:
        effective_lumo = None

    if effective_homo is None or effective_lumo is None:
        logger.info(
            "Cannot calculate chemical properties: "
            "missing SOMO or LUMO energy values."
        )
        return

    chemical_potential = 1 / 2 * (effective_lumo + effective_homo)
    chemical_hardness = 1 / 2 * (effective_lumo - effective_homo)
    electrophilicity_index = chemical_potential**2 / (2 * chemical_hardness)

    logger.info(
        f"Chemical potential, mu: {chemical_potential:.4} {energy_unit}"
    )
    logger.info(
        f"Chemical hardness, eta: {chemical_hardness:.4} {energy_unit}"
    )
    logger.info(
        f"Electrophilicity Index, omega: {electrophilicity_index:.4} "
        f"{energy_unit}"
    )


@click.command()
@click.option(
    "-f",
    "--filename",
    required=True,
    default=None,
    type=str,
    help="Gaussian or ORCA output file.",
)
@click.option(
    "-u",
    "--unit",
    default="eV",
    type=click.Choice(["eV", "kcal/mol"], case_sensitive=False),
    help="Unit of FMO energy.",
)
def entry_point(filename, unit):
    """
    Calculate and display frontier molecular orbital (FMO) properties.

    Supports both closed-shell and open-shell (radical) systems.
    For open-shell systems, displays SOMO energies and separate alpha/beta
    HOMO/LUMO values.
    """
    create_logger()
    program = get_outfile_format(filename)
    if program == "gaussian":
        outputfile = Gaussian16Output(filename=filename)
    elif program == "orca":
        outputfile = ORCAOutput(filename=filename)
    else:
        raise TypeError(f"File {filename} is of unknown filetype.")

    energy_unit = "eV" if unit.lower() == "ev" else "kcal/mol"

    # Check if the system is open-shell (multiplicity != 1)
    multiplicity = outputfile.multiplicity
    if multiplicity == 1:
        _display_closed_shell_fmo(outputfile, unit, energy_unit)
    else:
        _display_open_shell_fmo(outputfile, unit, energy_unit)


if __name__ == "__main__":
    entry_point()
