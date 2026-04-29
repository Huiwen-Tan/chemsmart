import functools
import logging
import os

import click

from chemsmart.database.export import CSV_OPTIONAL_COLUMNS, DatabaseExporter
from chemsmart.utils.cli import MyCommand

from .database import database

logger = logging.getLogger(__name__)


def click_export_options(f):
    """Common click options for database export."""

    @click.option(
        "-f",
        "--file",
        type=str,
        required=True,
        help="Path to the input database file (.db).",
    )
    @click.option(
        "--ri",
        "--record-index",
        "record_index",
        type=int,
        default=None,
        help="Record index (1-based) to export.",
    )
    @click.option(
        "--rid",
        "--record-id",
        "record_id",
        type=str,
        default=None,
        help="Record ID (or prefix, at least 12 chars) to export.",
    )
    @click.option(
        "--si",
        "--structure-index",
        "structure_index",
        type=str,
        default="-1",
        help="Structure index (1-based) within the record. Default: -1 (last structure).",
    )
    @click.option(
        "-k",
        "--keys",
        type=str,
        default=None,
        help=(
            "Comma-separated scalar keys for CSV export. "
            f"Supported: {', '.join(sorted(CSV_OPTIONAL_COLUMNS))}"
        ),
    )
    @click.option(
        "-o",
        "--output",
        type=str,
        required=True,
        help="Output file path. Format inferred from extension (.json, .csv, .xyz).",
    )
    @functools.wraps(f)
    def wrapper_common_options(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper_common_options


@database.command(cls=MyCommand)
@click_export_options
@click.pass_context
def export(ctx, file, record_index, record_id, structure_index, keys, output):
    """Export records from a chemsmart database.

    The output format is inferred from the file extension of -o/--output:

    \b
      .json  – Full record data (or filtered by --ri/--rid)
      .csv   – Scalar properties table (one row per record)
      .xyz   – Structure coordinates (single or multiple as frames; requires --ri/--rid)

    \b
    Default CSV columns: record_index, record_id, chemical_formula.
    Use -k to add extra scalar columns.

    \b
    Supported CSV keys:
      program, functional, basis, charge, multiplicity, smiles,
      total_energy, homo_energy, lumo_energy, fmo_gap,
      zero_point_energy, enthalpy, entropy, gibbs_free_energy

    \b
    Examples:
        chemsmart run database export -f my.db -o my.json
        chemsmart run database export -f my.db --ri 4 -o mol.xyz
        chemsmart run database export -f my.db --ri 4 --si ':' -o trajectory.xyz
        chemsmart run database export -f my.db -k total_energy,homo_energy,lumo_energy -o training_set.csv
    """
    # Validate input database
    file = os.path.abspath(file)
    if not os.path.isfile(file):
        raise click.UsageError(f"Database file not found: {file}")

    from chemsmart.database.utils import is_chemsmart_database

    if not is_chemsmart_database(file):
        raise click.UsageError(
            f"File {file} is not a valid chemsmart database file."
        )

    # Mutual exclusivity: --ri and --rid
    if record_index is not None and record_id is not None:
        raise click.UsageError(
            "Options --ri/--record-index and --rid/--record-id are mutually exclusive."
        )

    # XYZ format requires --ri/--rid
    ext = os.path.splitext(output)[1].lower()
    if ext == ".xyz":
        if record_index is None and record_id is None:
            raise click.UsageError(
                "XYZ export requires --ri/--record-index or --rid/--record-id to select a record."
            )

    output = os.path.abspath(output)

    exporter = DatabaseExporter(
        db_file=file,
        output=output,
        record_index=record_index,
        record_id=record_id,
        structure_index=structure_index,
        keys=keys,
    )

    exporter.export()
    logger.info(f"Exported to {os.path.basename(output)}.")

    return None
