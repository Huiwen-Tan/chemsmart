"""
XTB Module Usage Examples
==========================

This file demonstrates how to use the XTB module in chemsmart.

Basic Concepts
--------------
The xTB module provides an interface to run xTB calculations with API consistency
similar to Gaussian and ORCA modules. Key differences:

1. Lightweight & Auto-detection: xTB is usually installed in the environment, 
   and the module automatically detects the executable from PATH.

2. Command-line Driven: Unlike Gaussian/ORCA which use input files, xTB tasks 
   are submitted via command-line arguments.

3. Directory-based Execution: xTB generates multiple output files in the current 
   working directory.

Usage Examples
--------------
"""

# Example 1: Single Point Energy Calculation
# ------------------------------------------
from chemsmart.io.molecules.structure import Molecule
from chemsmart.jobs.xtb import XTBSinglePointJob
from chemsmart.jobs.xtb.settings import XTBJobSettings

# Load a molecule
molecule = Molecule.from_filepath("water.xyz")

# Create settings for single point calculation
settings = XTBJobSettings.sp(
    gfn_version="gfn2",  # GFN2-xTB Hamiltonian
    charge=0,            # Neutral molecule
    uhf=0,               # Singlet (no unpaired electrons)
)

# Create the job
job = XTBSinglePointJob(
    molecule=molecule,
    settings=settings,
    label="water_sp"
)

# Run the job (requires server configuration)
# job.run()

# Access results
# output = job.output()
# energy = output.total_energy  # in Hartree
# homo = output.homo_energy     # in eV
# lumo = output.lumo_energy     # in eV


# Example 2: Geometry Optimization
# ---------------------------------
from chemsmart.jobs.xtb import XTBOptJob

# Create settings for optimization
settings = XTBJobSettings.opt(
    gfn_version="gfn2",
    optimization_level="tight",  # Options: crude, sloppy, loose, normal, tight, vtight, extreme
    charge=0,
    uhf=0,
)

# Create the optimization job
job = XTBOptJob(
    molecule=molecule,
    settings=settings,
    label="water_opt"
)

# Run and access results
# job.run()
# output = job.output()
# optimized_structure = output.get_molecule(index="-1")  # Last geometry
# final_energy = output.total_energy
# converged = output.geometry_optimization_converged


# Example 3: Frequency Calculation
# ---------------------------------
from chemsmart.jobs.xtb import XTBFreqJob

settings = XTBJobSettings.freq(
    gfn_version="gfn2",
    charge=0,
    uhf=0,
)

job = XTBFreqJob(
    molecule=molecule,
    settings=settings,
    label="water_freq"
)

# Run and access results
# job.run()
# output = job.output()
# frequencies = output.vibrational_frequencies  # in cm^-1
# ir_intensities = output.ir_intensities
# zero_point_energy = output.zero_point_energy  # in Hartree


# Example 4: Solvent Model (GBSA or ALPB)
# ----------------------------------------
settings = XTBJobSettings.opt(
    gfn_version="gfn2",
    optimization_level="normal",
    charge=0,
    uhf=0,
    solvent_model="gbsa",    # or "alpb"
    solvent_id="water",      # or "acetonitrile", "methanol", etc.
)

job = XTBOptJob(
    molecule=molecule,
    settings=settings,
    label="water_opt_solv"
)


# Example 5: Using the Factory Method
# ------------------------------------
from chemsmart.jobs.xtb import XTBJob

# Create a job from job type string
settings = XTBJobSettings.default()
settings.job_type = "opt"
settings.optimization_level = "normal"

job = XTBJob.from_jobtype(
    jobtype="opt",          # "sp", "opt", or "freq"
    molecule=molecule,
    settings=settings,
    label="water_opt_factory"
)


# Example 6: Accessing Output Files
# ----------------------------------
from chemsmart.io.xtb import XTBOutput, XTBFolder

# From a folder containing XTB output files
folder = XTBFolder("water_opt")
if folder.has_xtb_output():
    output = XTBOutput(folder=folder.folder)
    
    # Access various properties
    energy = output.total_energy
    homo_lumo_gap = output.fmo_gap
    
    # Check for optimization results
    if folder.has_optimization_trajectory():
        all_structures = output.all_structures
        
    # Check for frequency results  
    if folder.has_hessian():
        frequencies = output.vibrational_frequencies

# From a specific output file
output = XTBOutput(filename="water_opt/water_opt.out")


# Example 7: Custom Settings
# ---------------------------
# For advanced users who need full control
settings = XTBJobSettings(
    gfn_version="gfn2",
    optimization_level="vtight",
    charge=-1,           # Anion
    uhf=0,              # Singlet
    job_type="opt",
    title="Custom XTB Optimization",
    freq=False,
    solvent_model="alpb",
    solvent_id="acetonitrile",
)


# Key XTB Settings Parameters
# ----------------------------
"""
- gfn_version: "gfn0", "gfn1", "gfn2" (default), "gfnff"
- optimization_level: "crude", "sloppy", "loose", "normal", "tight", "vtight", "extreme"
- charge: Integer (default: 0)
- uhf: Number of unpaired electrons (default: 0)
- job_type: "opt" for optimization, "hess" for frequencies, None for SP
- freq: Boolean, whether to compute frequencies
- solvent_model: "gbsa" or "alpb"
- solvent_id: Solvent name (e.g., "water", "acetonitrile", "methanol")
"""


# Supported Solvents (GBSA/ALPB)
# -------------------------------
"""
Common solvents supported by xTB:
- Water, Acetone, Acetonitrile, Aniline, Benzaldehyde, Benzene
- CH2Cl2, CHCl3, CS2, Dioxane, DMF, DMSO, Ether
- Ethanol, Furane, Hexadecane, Hexane, Methanol
- Nitromethane, Octanol, Phenol, Toluene, THF
- And many more...

Check xTB documentation for full list.
"""


# Output Properties Available
# ----------------------------
"""
Energy and Electronic Properties:
- total_energy, scc_energy, repulsion_energy
- homo_energy, lumo_energy, fmo_gap
- c6_coefficient, c8_coefficient, alpha_coefficient

Optimization Results:
- geometry_optimization_converged
- optimized_structure_block
- all_structures (trajectory)
- molecular_mass, center_of_mass, moments_of_inertia

Frequency/Thermodynamics:
- vibrational_frequencies
- ir_intensities, raman_intensities
- zero_point_energy
- total_enthalpy, total_free_energy

Solvent Properties:
- solvent_model, solvent_id, dielectric_constant
- solvation_energy_gsolv
- electronic_solvation_energy_gelec

Multipole Moments:
- total_molecular_dipole_moment
- full_molecular_dipole
- full_molecular_quadrupole

And many more...
"""
