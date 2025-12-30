# XTB Module for Chemsmart

## Overview

The XTB module provides a Python interface to run xTB (extended tight-binding) quantum chemistry calculations through chemsmart, with API consistency similar to the Gaussian and ORCA modules.

## Key Features

### 1. Lightweight & Auto-detection
- xTB executable is automatically detected from your `$PATH`
- No manual configuration needed if xTB is already installed
- Falls back to server configuration if needed

### 2. Command-line Driven
- Unlike Gaussian/ORCA which use input files, xTB uses command-line arguments
- The module automatically builds proper command strings from settings

### 3. Directory-based Execution
- Each job runs in its own dedicated directory
- Multiple output files are properly managed (xtbopt.log, xtbopt.xyz, charges, etc.)

### 4. Comprehensive Result Parsing
- Extracts energies, geometries, frequencies, and more
- Supports optimization trajectories
- Parses solvent model results
- Handles thermodynamic properties

## Installation

Ensure xTB is installed and available in your PATH:

```bash
# On conda:
conda install -c conda-forge xtb

# Or download from: https://github.com/grimme-lab/xtb
```

## Quick Start

```python
from chemsmart.io.molecules.structure import Molecule
from chemsmart.jobs.xtb import XTBOptJob
from chemsmart.jobs.xtb.settings import XTBJobSettings

# Load molecule
molecule = Molecule.from_filepath("water.xyz")

# Create settings
settings = XTBJobSettings.opt(
    gfn_version="gfn2",
    optimization_level="tight",
    charge=0,
    uhf=0
)

# Create and run job
job = XTBOptJob(molecule=molecule, settings=settings, label="water_opt")
# job.run()  # Requires server configuration

# Access results
# output = job.output()
# energy = output.total_energy
# optimized_geometry = output.get_molecule(index="-1")
```

## Supported Job Types

### Single Point Energy (SP)
```python
settings = XTBJobSettings.sp(charge=0, uhf=0)
job = XTBSinglePointJob(molecule, settings, label="mol_sp")
```

### Geometry Optimization (Opt)
```python
settings = XTBJobSettings.opt(optimization_level="tight")
job = XTBOptJob(molecule, settings, label="mol_opt")
```

### Frequency Calculation (Freq/Hess)
```python
settings = XTBJobSettings.freq()
job = XTBFreqJob(molecule, settings, label="mol_freq")
```

## Settings Parameters

### Core Parameters
- `gfn_version`: GFN Hamiltonian version
  - Options: `"gfn0"`, `"gfn1"`, `"gfn2"` (default), `"gfnff"`
  
- `charge`: Molecular charge (default: 0)
  
- `uhf`: Number of unpaired electrons (default: 0)
  - For singlet: `uhf=0`
  - For doublet: `uhf=1`
  - For triplet: `uhf=2`

### Optimization Parameters
- `optimization_level`: Convergence threshold
  - Options: `"crude"`, `"sloppy"`, `"loose"`, `"normal"` (default), `"tight"`, `"vtight"`, `"extreme"`

### Solvent Models
```python
settings = XTBJobSettings.opt(
    solvent_model="gbsa",  # or "alpb"
    solvent_id="water"     # solvent name
)
```

Supported solvents include: water, acetonitrile, methanol, ethanol, DMSO, acetone, CHCl3, and many more.

## Output Properties

### Energy Properties
- `total_energy`: Total energy in Hartree
- `homo_energy`, `lumo_energy`: Frontier orbital energies in eV
- `fmo_gap`: HOMO-LUMO gap in eV

### Optimization Results
- `geometry_optimization_converged`: Boolean
- `all_structures`: List of all optimization steps
- `get_molecule(index="-1")`: Get final optimized geometry

### Frequency Results
- `vibrational_frequencies`: List of frequencies in cm⁻¹
- `ir_intensities`: IR intensities
- `zero_point_energy`: ZPE in Hartree
- `total_enthalpy`, `total_free_energy`: Thermodynamic properties

### Solvent Properties
- `solvent_model`, `solvent_id`: Solvent information
- `solvation_energy_gsolv`: Solvation free energy

## File Structure

After running an XTB job, you'll find these files in the job directory:

- `{label}.xyz`: Input structure
- `{label}.out`: Main output file
- `{label}.err`: Error/warning messages
- `xtbopt.log`: Optimization trajectory (for opt jobs)
- `xtbopt.xyz` or `xtbopt.coord`: Final optimized structure
- `charges`: Atomic partial charges
- `wbo`: Wiberg bond orders
- `hessian`: Hessian matrix (for freq jobs)
- `gradient`: Energy gradient

## API Consistency

The XTB module follows the same patterns as Gaussian and ORCA:

```python
# Similar to GaussianOptJob and ORCAOptJob
from chemsmart.jobs.xtb import XTBOptJob
from chemsmart.jobs.gaussian import GaussianOptJob
from chemsmart.jobs.orca import ORCAOptJob

# All share the same interface
for JobClass in [XTBOptJob, GaussianOptJob, ORCAOptJob]:
    job = JobClass(molecule, settings, label="opt")
    # job.run()
    # output = job.output()
```

## Advanced Usage

### Custom Settings
```python
settings = XTBJobSettings(
    gfn_version="gfn2",
    optimization_level="vtight",
    charge=-1,
    uhf=0,
    job_type="opt",
    title="Advanced XTB Job",
    freq=False,
    solvent_model="alpb",
    solvent_id="acetonitrile",
)
```

### Factory Method
```python
from chemsmart.jobs.xtb import XTBJob

job = XTBJob.from_jobtype(
    jobtype="opt",  # "sp", "opt", or "freq"
    molecule=molecule,
    settings=settings,
    label="job"
)
```

### Direct Output Reading
```python
from chemsmart.io.xtb import XTBOutput

# From folder
output = XTBOutput(folder="path/to/job/folder")

# From specific file
output = XTBOutput(filename="path/to/output.out")

# Access properties
energy = output.total_energy
frequencies = output.vibrational_frequencies
```

## Differences from Gaussian/ORCA

1. **No Input File**: xTB uses command-line arguments instead of .com/.inp files
2. **Auto-detection**: xTB is typically in PATH, no server config required
3. **Multiple Output Files**: xTB generates several output files (charges, wbo, etc.)
4. **Fast Calculations**: xTB is much faster but less accurate than DFT methods

## References

- xTB Documentation: https://xtb-docs.readthedocs.io/
- xTB GitHub: https://github.com/grimme-lab/xtb
- GFN2-xTB Paper: J. Chem. Theory Comput. 2019, 15, 3, 1652–1671

## Module Structure

```
chemsmart/
├── io/xtb/
│   ├── __init__.py      # Exports and references
│   ├── input.py         # XTB input file parser
│   ├── output.py        # XTB output file parser
│   └── folder.py        # XTB folder management
└── jobs/xtb/
    ├── __init__.py      # Job class exports
    ├── job.py           # Base XTBJob class
    ├── settings.py      # XTBJobSettings
    ├── runner.py        # XTBJobRunner
    ├── opt.py           # XTBOptJob
    ├── singlepoint.py   # XTBSinglePointJob
    ├── freq.py          # XTBFreqJob
    └── USAGE_EXAMPLES.py # Detailed examples
```
