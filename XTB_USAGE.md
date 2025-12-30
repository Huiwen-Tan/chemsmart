# xTB Module Usage Examples

This document demonstrates how to use the xTB module in chemsmart for semi-empirical quantum chemistry calculations.

## Overview

The xTB module provides a consistent API similar to Gaussian and ORCA modules, allowing users to:
- Perform single point energy calculations
- Run geometry optimizations
- Use various GFN methods (GFN0, GFN1, GFN2, GFN-FF)
- Apply implicit solvation (ALPB model)
- Auto-detect xTB executable from PATH

## Basic Usage

### 1. Simple Geometry Optimization

```python
from chemsmart.jobs.xtb import XTBOptJob
from chemsmart.io.molecules.structure import Molecule

# Load a molecule
molecule = Molecule.from_filepath("molecule.xyz")

# Create and run optimization job
job = XTBOptJob(molecule=molecule, label="my_optimization")
# job.run()  # Would execute if jobrunner is configured
```

### 2. Single Point Energy Calculation

```python
from chemsmart.jobs.xtb import XTBSinglePointJob
from chemsmart.settings.xtb import XTBJobSettings

# Custom settings
settings = XTBJobSettings(
    method="GFN2-xTB",
    task="sp",
    charge=0,
    multiplicity=1
)

job = XTBSinglePointJob(
    molecule=molecule,
    settings=settings,
    label="single_point"
)
```

### 3. Using Different Methods

```python
# GFN1-xTB method
settings_gfn1 = XTBJobSettings(method="GFN1-xTB", task="opt")

# GFN0-xTB method (faster, less accurate)
settings_gfn0 = XTBJobSettings(method="GFN0-xTB", task="opt")

# GFN-FF force field (very fast)
settings_gfnff = XTBJobSettings(method="GFN-FF", task="opt")
```

### 4. Implicit Solvation

```python
# Optimization in water using ALPB implicit solvation
settings = XTBJobSettings(
    method="GFN2-xTB",
    task="opt",
    solvent="water"
)

job = XTBOptJob(molecule=molecule, settings=settings, label="opt_in_water")
```

### 5. Charged and Open-Shell Systems

```python
# Cation with doublet spin state
settings = XTBJobSettings(
    method="GFN2-xTB",
    task="opt",
    charge=1,
    multiplicity=2  # One unpaired electron
)

job = XTBOptJob(molecule=molecule, settings=settings, label="cation_opt")
```

## Advanced Usage

### Custom Optimization Levels

```python
settings = XTBJobSettings(
    method="GFN2-xTB",
    task="opt",
    opt_level="tight",  # Options: crude, sloppy, loose, normal, tight, vtight, extreme
    accuracy=0.1,        # Numerical accuracy
)
```

### Frequency Calculations

```python
# Hessian calculation (frequencies)
settings = XTBJobSettings(
    method="GFN2-xTB",
    task="hess",
    charge=0,
    multiplicity=1
)

# Or optimization followed by frequencies
settings = XTBJobSettings(
    method="GFN2-xTB",
    task="ohess",  # Optimization + Hessian
)
```

### Parallel Execution

```python
settings = XTBJobSettings(
    method="GFN2-xTB",
    task="opt",
    parallel=4  # Use 4 threads
)
```

## Output Parsing

### Reading Results

```python
from chemsmart.io.xtb.output import XTBOutput

# Parse output file
output = XTBOutput("my_calculation.out", job_folder="./")

# Check if job completed successfully
if output.normal_termination:
    print(f"Job completed successfully!")
    print(f"Final energy: {output.energy} Eh")
    
    # Get optimized structure
    opt_structure = output.optimized_structure
    if opt_structure:
        opt_structure.write("optimized.xyz")
    
    # Get frequencies (if calculated)
    if output.frequencies:
        print(f"Frequencies: {output.frequencies} cm^-1")
    
    # Get charges
    if output.charges:
        print(f"Mulliken charges: {output.charges.get('mulliken')}")
        print(f"CM5 charges: {output.charges.get('cm5')}")
```

## Integration with JobRunner

### Setting up xTB with a Server

1. Create a server configuration file (e.g., `local.yaml`) in your user settings directory:

```yaml
XTB:
  EXEFOLDER: /path/to/xtb/bin  # Optional if xTB is in PATH
  MODULES: ""
  SCRIPTS: ""
  ENVARS: |
    export OMP_NUM_THREADS=4
  SCRATCH: /tmp/scratch
```

2. If xTB is in your PATH, the executable will be auto-detected and you can omit EXEFOLDER.

### Running Jobs with JobRunner

```python
from chemsmart.jobs.xtb import XTBOptJob, XTBJobRunner
from chemsmart.settings.server import Server

# Create job
job = XTBOptJob(molecule=molecule, label="my_opt")

# Create runner
server = Server.current()  # Or Server.from_servername("local")
runner = XTBJobRunner(server=server, scratch=False)

# Run job
runner.run(job)
```

## Command-Line Interface

The xTB module generates appropriate command-line arguments:

```bash
# Example generated command for optimization with GFN2-xTB in water:
xtb molecule.xyz --opt --gfn 2 --chrg 0 --alpb water
```

## Available Solvents for ALPB Model

Common solvents supported by xTB's ALPB implicit solvation:
- water
- methanol
- ethanol
- acetone
- acetonitrile
- dmso
- chcl3
- thf
- and many more (see xTB documentation)

## Comparison with Gaussian/ORCA

The xTB module follows the same design patterns:

| Feature | Gaussian | ORCA | xTB |
|---------|----------|------|-----|
| Job Creation | `GaussianOptJob(...)` | `ORCAOptJob(...)` | `XTBOptJob(...)` |
| Settings | `GaussianJobSettings(...)` | `ORCAJobSettings(...)` | `XTBJobSettings(...)` |
| Output Parsing | `Gaussian16Output(...)` | `ORCAOutput(...)` | `XTBOutput(...)` |
| Factory Methods | `from_filename()`, `from_pubchem()` | ✓ | ✓ |
| Job Runner | `GaussianJobRunner` | `ORCAJobRunner` | `XTBJobRunner` |

## Notes

- xTB is command-line driven (no input file generation needed beyond xyz coordinates)
- xTB generates multiple output files in the execution directory
- The runner automatically copies important output files from scratch back to the job folder
- xTB executable auto-detection works if `xtb` is in your system PATH
