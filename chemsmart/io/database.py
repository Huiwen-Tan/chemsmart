from functools import cached_property

import numpy as np

from chemsmart.database.database import Database
from chemsmart.database.utils import resolve_record
from chemsmart.utils.mixins import FileMixin
from chemsmart.utils.utils import string2index_1based


class DatabaseFile(FileMixin):
    """Chemsmart database file object."""

    def __init__(self, filename):
        self.filename = filename

    @cached_property
    def last_structure(self):
        """Return the last molecular structure from the record(s)."""
        return self.get_molecules(index="-1")

    @property
    def molecule(self):
        """Alias for the last molecular structure."""
        return self.last_structure

    def get_molecules(
        self,
        index=":",
        return_list=False,
        record_index=None,
        record_id=None,
    ):
        from chemsmart.io.molecules.structure import Molecule

        def build_molecule_from_database(struct_dict):
            """Convert a structure dictionary from the database to a Molecule object."""
            vibrational_modes = struct_dict.get("vibrational_modes")
            if vibrational_modes is not None:
                vibrational_modes = [
                    np.array(mode) for mode in vibrational_modes
                ]
            return Molecule(
                symbols=struct_dict.get("chemical_symbols"),
                positions=np.array(struct_dict.get("positions")),
                charge=struct_dict.get("charge"),
                multiplicity=struct_dict.get("multiplicity"),
                energy=struct_dict.get("energy"),
                forces=(
                    np.array(struct_dict["forces"])
                    if struct_dict.get("forces")
                    else None
                ),
                frozen_atoms=struct_dict.get("frozen_atoms"),
                vibrational_frequencies=struct_dict.get(
                    "vibrational_frequencies"
                ),
                vibrational_modes=vibrational_modes,
                mulliken_atomic_charges=struct_dict.get(
                    "mulliken_atomic_charges"
                ),
                rotational_symmetry_number=struct_dict.get(
                    "rotational_symmetry_number"
                ),
                is_optimized_structure=struct_dict.get(
                    "is_optimized_structure"
                ),
                structure_index_in_file=struct_dict.get(
                    "structure_index_in_file"
                ),
            )

        db = Database(self.filename)

        # Resolve record selection
        if record_index is not None or record_id is not None:
            records = resolve_record(
                db,
                record_index=record_index,
                record_id=record_id,
                return_list=True,
            )
        else:
            records = db.get_all_records()

        molecules = []
        index = string2index_1based(index)
        for record in records:
            mol_dicts = record.get("molecules", [])
            if not mol_dicts:
                continue
            if isinstance(index, int):
                try:
                    molecule = build_molecule_from_database(mol_dicts[index])
                    molecules.append(molecule)
                except IndexError:
                    raise ValueError(
                        f"Structure index '{index}' out of range for record {record.get('record_index')}"
                    )
            elif isinstance(index, slice):
                molecule = [
                    build_molecule_from_database(mol_dict)
                    for mol_dict in mol_dicts[index]
                ]
                molecules.extend(molecule)
        if return_list:
            return molecules
        else:
            if len(molecules) == 1:
                return molecules[0]
            return molecules
