"""
Database export module for exporting records from a chemsmart database.

Supports exporting to JSON, CSV, and XYZ formats. The output format is
inferred from the file extension of the output path.
"""

import csv
import json
import logging
import os

from chemsmart.database.database import Database
from chemsmart.database.utils import convert_numpy, resolve_record

logger = logging.getLogger(__name__)

# Scalar keys supported for CSV export (from records + last molecule).
CSV_OPTIONAL_COLUMNS = {
    "program",
    "functional",
    "basis",
    "charge",
    "multiplicity",
    "smiles",
    "total_energy",
    "homo_energy",
    "lumo_energy",
    "fmo_gap",
    "zero_point_energy",
    "enthalpy",
    "entropy",
    "gibbs_free_energy",
}

# Default columns always present in CSV output.
CSV_DEFAULT_COLUMNS = ["record_index", "record_id", "chemical_formula"]

SUPPORTED_FORMATS = {".json", ".csv", ".xyz"}


class DatabaseExporter:
    """Export records from a chemsmart database to JSON, CSV, or XYZ.

    Args:
        db_file: Path to the input ``.db`` file.
        output: Output file path (extension determines format).
        record_index: 1-based record index (mutually exclusive with *record_id*).
        record_id: Record ID or prefix (mutually exclusive with *record_index*).
        structure_index: 1-base structure index within a record (XYZ export).
        keys: Comma-separated string of extra scalar keys for CSV.
    """

    def __init__(
        self,
        db_file,
        output,
        record_index=None,
        record_id=None,
        structure_index=None,
        keys=None,
    ):
        self.db = Database(db_file)
        self.output = output
        self.record_index = record_index
        self.record_id = record_id
        self.structure_index = structure_index
        self.keys = keys
        self.format = self.infer_format()
        self.parsed_keys = self.parse_csv_keys()

    def export(self):
        """Run the export, assigning to the appropriate format handler."""
        handler = {
            ".json": self.to_json,
            ".csv": self.to_csv,
            ".xyz": self.to_xyz,
        }
        handler[self.format]()

    def to_json(self):
        """Export all (or selected) records to a JSON file."""
        data = self.get_records()
        converted = convert_numpy(data)
        with open(self.output, "w") as f:
            json.dump(converted, f, indent=4)

    def to_csv(self):
        """Export scalar properties of all (or selected) records to CSV."""
        records = self.get_records()
        columns = list(CSV_DEFAULT_COLUMNS)
        if self.parsed_keys:
            columns.extend(self.parsed_keys)
        rows = [self.record_to_csv_row(rec, columns) for rec in records]
        with open(self.output, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns, restval="NaN")
            writer.writeheader()
            writer.writerows(rows)

    def to_xyz(self):
        """Export structure(s) from a record to an XYZ file."""
        from chemsmart.io.molecules.structure import Molecule

        if self.record_index is None and self.record_id is None:
            raise ValueError(
                "Either record_index or record_id must be provided for XYZ export"
            )
        mol = Molecule.from_filepath(
            self.db.db_file,
            index=self.structure_index,
            record_index=self.record_index,
            record_id=self.record_id,
        )

        # Handle multiple structures (list) or single structure
        if isinstance(mol, list):
            if not mol:
                raise ValueError("No structures found for the specified index")
            if len(mol) > 1:
                logger.info(
                    f"Exporting {len(mol)} structures as frames in XYZ file: "
                    f"{os.path.basename(self.output)}"
                )
                # Write multiple structures as frames
                for i, m in enumerate(mol):
                    mode = "w" if i == 0 else "a"
                    m.write_xyz(self.output, mode=mode)
            else:
                # Single structure from list
                mol[0].write_xyz(self.output, mode="w")
        else:
            # Single structure object
            mol.write_xyz(self.output, mode="w")

    def get_records(self):
        """Return full record dicts according to the current selection."""
        if self.record_index is not None or self.record_id is not None:
            return resolve_record(
                self.db,
                record_index=self.record_index,
                record_id=self.record_id,
                return_list=True,
            )
        return self.db.get_all_records()

    def infer_format(self):
        """Infer export format from file extension."""
        ext = os.path.splitext(self.output)[1].lower()
        if ext not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported output format '{ext}'. "
                f"Supported extensions: {', '.join(sorted(SUPPORTED_FORMATS))}"
            )
        return ext

    def parse_csv_keys(self):
        """Normalise the *keys* argument to a list or None."""
        if self.keys is not None:
            parsed_keys = [
                k.strip() for k in self.keys.split(",") if k.strip()
            ]
            # Validate
            invalid = set(parsed_keys) - CSV_OPTIONAL_COLUMNS
            if invalid:
                raise ValueError(
                    f"Unsupported CSV key(s): {', '.join(sorted(invalid))}. "
                    f"Supported: {', '.join(sorted(CSV_OPTIONAL_COLUMNS))}"
                )
            return parsed_keys
        return None

    @staticmethod
    def record_to_csv_row(record, columns):
        """Flatten a record dict into a single CSV row dict."""
        meta = record.get("meta", {})
        results = record.get("results", {})
        molecules = record.get("molecules", [])
        last_mol = molecules[-1] if molecules else {}
        lookup = {
            "record_index": record.get("record_index"),
            "record_id": record.get("record_id"),
            **meta,
            **results,
            "chemical_formula": last_mol.get("chemical_formula"),
            "charge": last_mol.get("charge"),
            "multiplicity": last_mol.get("multiplicity"),
            "smiles": last_mol.get("smiles"),
        }
        return {col: lookup.get(col, "NaN") for col in columns}
