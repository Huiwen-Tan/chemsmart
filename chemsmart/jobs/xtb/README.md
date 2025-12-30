# xTB Module for chemsmart

This module provides full integration of the xTB semi-empirical quantum chemistry program into the chemsmart toolkit.

## Features

### 1. Lightweight & Auto-detection
xTB executable is automatically detected from your system PATH. No manual configuration needed if xTB is already installed:

```python
from chemsmart.settings.xtb import XTBExecutable

# Auto-detect xTB
exe = XTBExecutable(auto_detect=True)
xtb_path = exe.get_executable()
```

### 2. Command-line Driven
Unlike Gaussian/ORCA which use input files, xTB is command-line driven. The module automatically builds command strings:

```python
from chemsmart.jobs.xtb.settings import XTBJobSettings

settings = XTBJobSettings(
    method='GFN2-xTB',
    job_type='opt',
    charge=-1,
    solvent_model='gbsa',
    solvent_id='water'
)

# Generates: --opt --gfn 2 --chrg -1 --gbsa water
command_args = settings.get_command_args()
```

### 3. Directory-based Execution
xTB generates multiple output files (xtbopt.xyz, charges, hessian, etc.). The runner manages these correctly:

```python
from chemsmart.jobs.xtb import XTBOptJob
from chemsmart.jobs.xtb.runner import XTBJobRunner

# Runner handles directory management automatically
job = XTBOptJob(molecule=mol, settings=settings, jobrunner=runner)
job.run()

# Access output files
output = job._output()
optimized_geom = output.optimized_geometry  # From xtbopt.xyz
charges = output.mulliken_charges            # From output
```

### 4. Result Extraction
Comprehensive output parser extracts all relevant data:

```python
from chemsmart.io.xtb.output import XTBOutput

output = XTBOutput('calculation.out', job_folder='path/to/job')

# Available properties
energy = output.energy                      # Total energy
opt_geom = output.optimized_geometry       # From xtbopt.xyz
freqs = output.frequencies                  # Vibrational frequencies
charges = output.mulliken_charges          # Mulliken charges
cm5 = output.cm5_charges                   # CM5 charges
dipole = output.dipole_moment              # Dipole moment
converged = output.optimization_converged  # Optimization status
```

### 5. API Consistency
The xTB module follows the same patterns as Gaussian and ORCA:

```python
from chemsmart.jobs.xtb import XTBOptJob
from chemsmart.io.molecules.structure import Molecule

# Create molecule
water = Molecule(symbols=['O', 'H', 'H'], positions=[[0,0,0], [1,0,0], [0,1,0]])

# Configure job - similar to Gaussian/ORCA
job = XTBOptJob(
    molecule=water,
    settings=XTBJobSettings(method='GFN2-xTB', job_type='opt'),
    label='water_opt',
    jobrunner=runner
)

# Run
job.run()

# Get results
output = job._output()
```

## Usage Examples

### Basic Single Point Calculation

```python
from chemsmart.jobs.xtb import XTBSinglePointJob
from chemsmart.jobs.xtb.settings import XTBJobSettings
from chemsmart.io.molecules.structure import Molecule

# Create molecule
water = Molecule(
    symbols=['O', 'H', 'H'],
    positions=[[0.0, 0.0, 0.0], [0.96, 0.0, 0.0], [-0.24, 0.93, 0.0]]
)

# Configure settings
settings = XTBJobSettings(
    method="GFN2-xTB",  # Options: GFN0-xTB, GFN1-xTB, GFN2-xTB, GFN-FF
    job_type="sp"
)

# Create and run job
job = XTBSinglePointJob(molecule=water, settings=settings, jobrunner=runner)
job.run()
```

### Geometry Optimization

```python
from chemsmart.jobs.xtb import XTBOptJob

settings = XTBJobSettings(
    method="GFN2-xTB",
    job_type="opt",
    optimization_level="tight"  # Options: crude, sloppy, loose, normal, tight, vtight, extreme
)

job = XTBOptJob(molecule=molecule, settings=settings, jobrunner=runner)
job.run()

# Get optimized geometry
output = job._output()
optimized_structure = output.optimized_geometry
```

### Solvated Calculations

```python
settings = XTBJobSettings(
    method="GFN2-xTB",
    job_type="sp",
    solvent_model="gbsa",  # or "alpb"
    solvent_id="water"     # Various solvents supported
)
```

### Charged Systems

```python
settings = XTBJobSettings(
    method="GFN2-xTB",
    job_type="opt",
    charge=-1,        # Molecular charge
    multiplicity=2    # Spin multiplicity (doublet)
)
```

### Frequency Calculations

```python
settings = XTBJobSettings(
    method="GFN2-xTB",
    job_type="freq"
)

job = XTBJob(molecule=molecule, settings=settings, jobrunner=runner)
job.run()

output = job._output()
frequencies = output.frequencies
```

### From File

```python
from chemsmart.jobs.xtb import XTBJob

# Create job from XYZ file
job = XTBJob.from_filename(
    filename="molecule.xyz",
    settings=settings,
    jobrunner=runner
)
job.run()
```

## Configuration

### Server Configuration

Add xTB to your server YAML file (`~/.chemsmart/server/yourserver.yaml`):

```yaml
xtb:
  EXEFOLDER: /path/to/xtb/bin
  LOCAL_RUN: true
  CONDA_ENV: null
  MODULES: null
  SCRIPTS: null
  ENVARS: |
    export OMP_NUM_THREADS=4
```

If xTB is in your PATH, configuration is optional as auto-detection will find it.

## Supported Methods

- **GFN0-xTB**: Minimal basis, very fast
- **GFN1-xTB**: Standard parametrization
- **GFN2-xTB**: Improved parametrization (default)
- **GFN-FF**: Force field method

## Supported Solvation Models

- **GBSA**: Generalized Born Surface Area
- **ALPB**: Analytical Linearized Poisson-Boltzmann

Common solvents: water, acetone, acetonitrile, aniline, benzaldehyde, benzene, ch2cl2, chcl3, cs2, dioxane, dmf, dmso, ether, ethylacetate, furane, hexadecane, hexane, methanol, nitromethane, octanol, woctanol, phenol, toluene, thf, ethanol

## Testing

Run the example script to test the implementation:

```bash
python examples/xtb_usage_examples.py
```

For unit testing with fake runner:

```python
from chemsmart.jobs.xtb.runner import FakeXTBJobRunner

# Use fake runner for testing without actual xTB installation
jobrunner = FakeXTBJobRunner(server=server, scratch=False)
```

## Files Generated by xTB

When running xTB calculations, the following files may be generated:

- `input.xyz`: Input geometry
- `output.out`: Main output file (captured stdout)
- `xtbopt.xyz`: Optimized geometry (for optimization jobs)
- `charges`: Atomic charges
- `wbo`: Wiberg bond orders
- `hessian`: Hessian matrix (for frequency calculations)
- `g98.out`: Gaussian-style output (if requested)
- Various other analysis files

The xTB module automatically manages these files and extracts relevant data.

## Module Structure

```
chemsmart/
├── io/xtb/
│   ├── __init__.py
│   └── output.py          # Output file parser
├── jobs/xtb/
│   ├── __init__.py
│   ├── job.py             # Base job classes
│   ├── settings.py        # Settings and command generation
│   ├── runner.py          # Job runner and fake runner
│   ├── writer.py          # Input file writer
│   ├── opt.py             # Optimization job
│   └── singlepoint.py     # Single point job
└── settings/
    └── xtb.py             # Executable configuration
```

## Differences from Gaussian/ORCA

1. **No input file**: xTB uses command-line arguments instead of input files
2. **Multiple output files**: Results are spread across several files in the working directory
3. **Simpler setup**: xTB is lightweight and often doesn't require complex configuration
4. **Fast execution**: xTB is designed for speed, ideal for large-scale screening

## Requirements

- Python 3.10+
- ASE (Atomic Simulation Environment)
- xTB program (optional for fake runner testing)

## Installation

The xTB module is included in chemsmart. Install chemsmart normally:

```bash
pip install -e .
```

To use real xTB calculations, install xTB separately:
- Download from: https://github.com/grimme-lab/xtb/releases
- Or use conda: `conda install -c conda-forge xtb`

## License

This module follows the same license as chemsmart.
