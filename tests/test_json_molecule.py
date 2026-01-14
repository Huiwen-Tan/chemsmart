"""
Tests for reading Molecule objects from JSON dataset files.
"""

import json
import os
import tempfile

import numpy as np
import pytest

from chemsmart.io.molecules.structure import Molecule


class TestJSONMolecule:
    """Test reading molecules from JSON files."""

    def test_read_single_molecule_from_json(self):
        """Test reading a single molecule from a JSON file."""
        # Create a temporary JSON file with a single molecule
        mol_data = {
            "symbols": ["C", "H", "H", "H", "H"],
            "positions": [
                [0.0, 0.0, 0.0],
                [1.09, 0.0, 0.0],
                [0.0, 1.09, 0.0],
                [0.0, 0.0, 1.09],
                [-0.5, -0.5, -0.5],
            ],
            "charge": 0,
            "multiplicity": 1,
            "energy": -40.5,
            "info": {"description": "Sample methane molecule"},
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(mol_data, f)
            temp_path = f.name

        try:
            # Read the molecule
            mol = Molecule.from_filepath(temp_path)

            # Verify molecule attributes
            assert isinstance(mol, Molecule)
            assert mol.chemical_formula == "CH4"
            assert mol.num_atoms == 5
            assert mol.charge == 0
            assert mol.multiplicity == 1
            assert mol.energy == -40.5
            assert len(mol.symbols) == 5
            assert mol.positions.shape == (5, 3)
            assert mol.info == {"description": "Sample methane molecule"}
        finally:
            os.unlink(temp_path)

    def test_read_single_molecule_return_list(self):
        """Test reading a single molecule with return_list=True."""
        mol_data = {
            "symbols": ["H", "H"],
            "positions": [[0.0, 0.0, 0.0], [0.74, 0.0, 0.0]],
            "charge": 0,
            "multiplicity": 1,
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(mol_data, f)
            temp_path = f.name

        try:
            mols = Molecule.from_filepath(temp_path, return_list=True)
            assert isinstance(mols, list)
            assert len(mols) == 1
            assert isinstance(mols[0], Molecule)
            assert mols[0].chemical_formula == "H2"
        finally:
            os.unlink(temp_path)

    def test_read_multiple_molecules_from_json(self):
        """Test reading multiple molecules from a JSON file."""
        mol_data = [
            {
                "symbols": ["H", "H"],
                "positions": [[0.0, 0.0, 0.0], [0.74, 0.0, 0.0]],
                "charge": 0,
                "multiplicity": 1,
                "energy": -1.1,
            },
            {
                "symbols": ["O", "O"],
                "positions": [[0.0, 0.0, 0.0], [1.21, 0.0, 0.0]],
                "charge": 0,
                "multiplicity": 3,
                "energy": -5.08,
            },
            {
                "symbols": ["N", "N"],
                "positions": [[0.0, 0.0, 0.0], [1.10, 0.0, 0.0]],
                "charge": 0,
                "multiplicity": 1,
                "energy": -4.52,
            },
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(mol_data, f)
            temp_path = f.name

        try:
            # Read all molecules
            mols = Molecule.from_filepath(temp_path, index=":", return_list=True)
            assert isinstance(mols, list)
            assert len(mols) == 3
            assert all(isinstance(m, Molecule) for m in mols)
            assert mols[0].chemical_formula == "H2"
            assert mols[1].chemical_formula == "O2"
            assert mols[2].chemical_formula == "N2"
            assert mols[0].energy == -1.1
            assert mols[1].energy == -5.08
            assert mols[2].energy == -4.52
        finally:
            os.unlink(temp_path)

    def test_read_molecule_by_index_last(self):
        """Test reading the last molecule using index=-1."""
        mol_data = [
            {
                "symbols": ["H", "H"],
                "positions": [[0.0, 0.0, 0.0], [0.74, 0.0, 0.0]],
            },
            {
                "symbols": ["O", "O"],
                "positions": [[0.0, 0.0, 0.0], [1.21, 0.0, 0.0]],
            },
            {
                "symbols": ["N", "N"],
                "positions": [[0.0, 0.0, 0.0], [1.10, 0.0, 0.0]],
            },
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(mol_data, f)
            temp_path = f.name

        try:
            mol = Molecule.from_filepath(temp_path, index="-1")
            assert isinstance(mol, Molecule)
            assert mol.chemical_formula == "N2"
        finally:
            os.unlink(temp_path)

    def test_read_molecule_by_index_first(self):
        """Test reading the first molecule using index=1."""
        mol_data = [
            {
                "symbols": ["H", "H"],
                "positions": [[0.0, 0.0, 0.0], [0.74, 0.0, 0.0]],
            },
            {
                "symbols": ["O", "O"],
                "positions": [[0.0, 0.0, 0.0], [1.21, 0.0, 0.0]],
            },
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(mol_data, f)
            temp_path = f.name

        try:
            mol = Molecule.from_filepath(temp_path, index="1")
            assert isinstance(mol, Molecule)
            assert mol.chemical_formula == "H2"
        finally:
            os.unlink(temp_path)

    def test_read_molecule_with_all_attributes(self):
        """Test reading a molecule with all possible attributes."""
        mol_data = {
            "symbols": ["C", "O"],
            "positions": [[0.0, 0.0, 0.0], [1.13, 0.0, 0.0]],
            "charge": 0,
            "multiplicity": 1,
            "energy": -113.3,
            "forces": [[0.1, 0.0, 0.0], [-0.1, 0.0, 0.0]],
            "velocities": [[0.01, 0.0, 0.0], [-0.01, 0.0, 0.0]],
            "frozen_atoms": [0, -1],
            "pbc_conditions": [0, 0, 0],
            "translation_vectors": None,
            "vibrational_frequencies": [2143.0],
            "vibrational_reduced_masses": [6.86],
            "vibrational_force_constants": [18.55],
            "vibrational_ir_intensities": [100.0],
            "vibrational_mode_symmetries": ["Sigma+"],
            "vibrational_modes": [[[0.0, 0.0, 0.71], [0.0, 0.0, -0.71]]],
            "info": {"source": "test", "method": "DFT"},
            "structure_index_in_file": 1,
            "rotational_symmetry_number": 1,
            "mulliken_atomic_charges": {"C1": -0.12, "O2": 0.12},
            "is_optimized_structure": True,
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(mol_data, f)
            temp_path = f.name

        try:
            mol = Molecule.from_filepath(temp_path)
            assert mol.chemical_formula == "CO"
            assert mol.charge == 0
            assert mol.multiplicity == 1
            assert mol.energy == -113.3
            assert mol.forces is not None
            assert mol.forces.shape == (2, 3)
            assert mol.velocities is not None
            assert mol.velocities.shape == (2, 3)
            assert mol.frozen_atoms == [0, -1]
            assert mol.pbc_conditions == [0, 0, 0]
            assert len(mol.vibrational_frequencies) == 1
            assert mol.vibrational_frequencies[0] == 2143.0
            assert len(mol.vibrational_modes) == 1
            assert np.array(mol.vibrational_modes[0]).shape == (2, 3)
            assert mol.info == {"source": "test", "method": "DFT"}
            assert mol.structure_index_in_file == 1
            assert mol.rotational_symmetry_number == 1
            assert mol.mulliken_atomic_charges == {"C1": -0.12, "O2": 0.12}
            assert mol.is_optimized_structure is True
        finally:
            os.unlink(temp_path)

    def test_json_missing_required_field_symbols(self):
        """Test that missing 'symbols' field raises ValueError."""
        mol_data = {
            "positions": [[0.0, 0.0, 0.0], [0.74, 0.0, 0.0]],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(mol_data, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="must include 'symbols' field"):
                Molecule.from_filepath(temp_path)
        finally:
            os.unlink(temp_path)

    def test_json_missing_required_field_positions(self):
        """Test that missing 'positions' field raises ValueError."""
        mol_data = {
            "symbols": ["H", "H"],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(mol_data, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="must include 'positions' field"):
                Molecule.from_filepath(temp_path)
        finally:
            os.unlink(temp_path)

    def test_json_empty_list(self):
        """Test that empty molecule list raises ValueError."""
        mol_data = []

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(mol_data, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Empty molecule list"):
                Molecule.from_filepath(temp_path)
        finally:
            os.unlink(temp_path)

    def test_json_invalid_type(self):
        """Test that invalid JSON type raises ValueError."""
        mol_data = "invalid string data"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(mol_data, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="must contain a dictionary"):
                Molecule.from_filepath(temp_path)
        finally:
            os.unlink(temp_path)

    def test_json_file_not_found(self):
        """Test that non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            Molecule.from_filepath("/nonexistent/path/to/file.json")

    def test_read_molecule_slice_notation(self):
        """Test reading molecules using slice notation."""
        mol_data = [
            {"symbols": ["H", "H"], "positions": [[0.0, 0.0, 0.0], [0.74, 0.0, 0.0]]},
            {"symbols": ["O", "O"], "positions": [[0.0, 0.0, 0.0], [1.21, 0.0, 0.0]]},
            {"symbols": ["N", "N"], "positions": [[0.0, 0.0, 0.0], [1.10, 0.0, 0.0]]},
            {"symbols": ["C", "O"], "positions": [[0.0, 0.0, 0.0], [1.13, 0.0, 0.0]]},
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(mol_data, f)
            temp_path = f.name

        try:
            # Read first two molecules
            mols = Molecule.from_filepath(temp_path, index="1:3", return_list=True)
            assert len(mols) == 2
            assert mols[0].chemical_formula == "H2"
            assert mols[1].chemical_formula == "O2"
        finally:
            os.unlink(temp_path)

    def test_positions_conversion_to_numpy_array(self):
        """Test that positions are correctly converted to numpy arrays."""
        mol_data = {
            "symbols": ["H", "H"],
            "positions": [[0.0, 0.0, 0.0], [0.74, 0.0, 0.0]],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(mol_data, f)
            temp_path = f.name

        try:
            mol = Molecule.from_filepath(temp_path)
            assert isinstance(mol.positions, np.ndarray)
            assert mol.positions.dtype == np.float64
            assert mol.positions.shape == (2, 3)
        finally:
            os.unlink(temp_path)

    def test_optional_none_fields(self):
        """Test that optional fields can be None or omitted."""
        mol_data = {
            "symbols": ["H", "H"],
            "positions": [[0.0, 0.0, 0.0], [0.74, 0.0, 0.0]],
            "charge": None,
            "multiplicity": None,
            "energy": None,
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(mol_data, f)
            temp_path = f.name

        try:
            mol = Molecule.from_filepath(temp_path)
            assert mol.chemical_formula == "H2"
            assert mol.charge is None
            assert mol.multiplicity is None
            assert mol.energy is None
        finally:
            os.unlink(temp_path)
