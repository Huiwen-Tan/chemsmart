# JSON Dataset Support for Molecule.from_filepath()

The `Molecule.from_filepath()` method now supports reading molecule data from JSON files. This allows you to store and load molecular structures along with their properties in a human-readable format.

## JSON Format

### Single Molecule
For a single molecule, use a JSON object with the following structure:

```json
{
  "symbols": ["C", "H", "H", "H", "H"],
  "positions": [
    [0.0, 0.0, 0.0],
    [0.629, 0.629, 0.629],
    [-0.629, -0.629, 0.629],
    [-0.629, 0.629, -0.629],
    [0.629, -0.629, -0.629]
  ],
  "charge": 0,
  "multiplicity": 1,
  "energy": -40.5175,
  "info": {
    "name": "Methane",
    "method": "B3LYP/6-31G*",
    "geometry": "optimized"
  }
}
```

### Multiple Molecules
For multiple molecules, use a JSON array of molecule objects:

```json
[
  {
    "symbols": ["H", "H"],
    "positions": [[0.0, 0.0, 0.0], [0.74, 0.0, 0.0]],
    "charge": 0,
    "multiplicity": 1,
    "energy": -1.1336
  },
  {
    "symbols": ["O", "O"],
    "positions": [[0.0, 0.0, 0.0], [1.208, 0.0, 0.0]],
    "charge": 0,
    "multiplicity": 3,
    "energy": -150.3254
  }
]
```

## Required Fields

- **symbols** (list of str): Atomic symbols for each atom
- **positions** (list of 3D coordinates): Atomic positions in Angstroms

## Optional Fields

All other Molecule attributes are optional:

- **charge** (int): Molecular charge
- **multiplicity** (int): Spin multiplicity
- **energy** (float): Total energy in eV
- **forces** (array): Atomic forces in eV/Å
- **velocities** (array): Atomic velocities
- **frozen_atoms** (list): Frozen atom indicators (-1 for frozen, 0 for relaxed)
- **pbc_conditions** (list): Periodic boundary conditions
- **translation_vectors** (list): Translation vectors for PBC
- **vibrational_frequencies** (list): Vibrational frequencies in cm⁻¹
- **vibrational_reduced_masses** (list): Reduced masses in amu
- **vibrational_force_constants** (list): Force constants
- **vibrational_ir_intensities** (list): IR intensities
- **vibrational_mode_symmetries** (list): Mode symmetries
- **vibrational_modes** (list of arrays): Normal mode displacement vectors
- **info** (dict): Additional metadata
- **structure_index_in_file** (int): Structure index
- **rotational_symmetry_number** (int): Rotational symmetry number
- **mulliken_atomic_charges** (dict): Mulliken charges per atom (e.g., {"C1": -0.12, "O2": 0.12})
- **is_optimized_structure** (bool): Whether structure is optimized

## Usage Examples

### Reading a Single Molecule

```python
from chemsmart.io.molecules.structure import Molecule

# Read single molecule
mol = Molecule.from_filepath('molecule.json')
print(f"Formula: {mol.chemical_formula}")
print(f"Energy: {mol.energy}")
```

### Reading Multiple Molecules

```python
# Read all molecules as a list
molecules = Molecule.from_filepath('molecules.json', index=':', return_list=True)
print(f"Loaded {len(molecules)} molecules")

# Read the last molecule
last_mol = Molecule.from_filepath('molecules.json', index='-1')

# Read the first molecule (1-based indexing)
first_mol = Molecule.from_filepath('molecules.json', index='1')

# Read a range of molecules (1-based indexing)
subset = Molecule.from_filepath('molecules.json', index='1:3', return_list=True)
```

## Index Notation

The `index` parameter supports Python slice notation (1-based):
- `"-1"` - Last molecule
- `"1"` - First molecule (1-based)
- `":"` - All molecules
- `"1:3"` - First three molecules (1-based, inclusive)
- `"2:"` - All molecules from the second onward

## Example Files

See `tests/data/JSONTests/` for example JSON dataset files:
- `single_molecule.json` - Single molecule example
- `sample_molecules.json` - Multiple molecules example with various properties

## Notes

- Positions and other array data are automatically converted to NumPy arrays
- All fields except `symbols` and `positions` are optional
- The JSON format is compatible with standard JSON parsers
- This format is useful for storing computed molecular properties alongside geometries
