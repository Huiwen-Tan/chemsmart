import functools
import logging
import os

import click

from chemsmart.database.inspect import DatabaseInspector
from chemsmart.utils.cli import MyCommand

from .database import database

logger = logging.getLogger(__name__)


def click_inspect_options(f):
    """Common click options for database inspect."""

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
        help="Record index (1-based) to inspect.",
    )
    @click.option(
        "--rid",
        "--record-id",
        "record_id",
        type=str,
        default=None,
        help="Record ID (or prefix, at least 12 chars) to inspect.",
    )
    @click.option(
        "--si",
        "--structure-index",
        "structure_index",
        type=int,
        default=None,
        help="Structure index (1-based) within the record.",
    )
    @functools.wraps(f)
    def wrapper_common_options(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper_common_options


@database.command(cls=MyCommand)
@click_inspect_options
@click.pass_context
def inspect(ctx, file, record_index, record_id, structure_index):
    """Inspect a chemsmart database, record, or structure.

    Without --ri/--rid, show a database overview (metadata and statistics).
    With --ri or --rid, show detailed information for one record.
    With --ri/--rid and --si, show detailed information for one structure.

    \b
    Examples:
        chemsmart run database inspect -f my.db
        chemsmart run database inspect -f my.db --ri 3
        chemsmart run database inspect -f my.db --rid a1b2c3d4e5f6
        chemsmart run database inspect -f my.db --ri 3 --si 1
    """
    # Validate input database
    file = os.path.abspath(file)
    if not os.path.isfile(file):
        raise click.UsageError(f"Database file not found: {file}")

    # Mutual exclusivity: --ri and --rid
    if record_index is not None and record_id is not None:
        raise click.UsageError(
            "Options --ri/--record-index and --rid/--record-id are mutually exclusive."
        )

    # --si requires --ri or --rid
    if (
        structure_index is not None
        and record_index is None
        and record_id is None
    ):
        raise click.UsageError(
            "Option --si/--structure-index requires --ri/--record-index or --rid/--record-id."
        )

    inspector = DatabaseInspector(
        file,
        index=record_index,
        record_id=record_id,
        structure_index=structure_index,
    )

    if record_index is None and record_id is None:
        # Database overview
        logger.info(
            f"Displaying database overview for {os.path.basename(file)}."
        )
        print(inspector.format_overview())
    elif structure_index is None:
        # Record detail
        if record_index is not None:
            logger.info(
                f"Displaying record at index {record_index} from {os.path.basename(file)}."
            )
        else:
            logger.info(
                f"Displaying record with ID {record_id} from {os.path.basename(file)}."
            )
        print(inspector.format_record_detail())
    else:
        # Structure detail
        if record_index is not None:
            logger.info(
                f"Displaying structure {structure_index} from record at index {record_index} in {os.path.basename(file)}."
            )
        else:
            logger.info(
                f"Displaying structure {structure_index} from record with ID {record_id} in {os.path.basename(file)}."
            )
        print(inspector.format_structure_detail())

    return None
