#!/usr/bin/env python3
"""
Example usage of the xTB module in chemsmart.

This script demonstrates how to use the xTB module for various
types of calculations, showing API consistency with Gaussian/ORCA.
"""

import os
import sys

# Add the chemsmart module to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chemsmart.io.molecules.structure import Molecule
from chemsmart.jobs.xtb import XTBJob, XTBOptJob, XTBSinglePointJob
from chemsmart.jobs.xtb.settings import XTBJobSettings
from chemsmart.jobs.xtb.runner import XTBJobRunner, FakeXTBJobRunner
from chemsmart.settings.server import Server
from chemsmart.settings.xtb import XTBExecutable


def example_1_basic_single_point():
    """Example 1: Basic single point calculation."""
    print("=" * 60)
    print("Example 1: Basic Single Point Calculation")
    print("=" * 60)
    
    # Create a water molecule
    water = Molecule(
        symbols=['O', 'H', 'H'],
        positions=[
            [0.0, 0.0, 0.0],
            [0.96, 0.0, 0.0],
            [-0.24, 0.93, 0.0]
        ]
    )
    
    # Create settings for GFN2-xTB single point
    settings = XTBJobSettings(
        method="GFN2-xTB",
        job_type="sp",
        charge=0,
        multiplicity=1
    )
    
    # Create a server configuration
    server = Server(
        name='local',
        scheduler='LOCAL',
        queue_name='local',
        num_hours=1,
        mem_gb=2,
        num_cores=1,
        num_gpus=0
    )
    
    # Create job runner (using fake runner for demonstration)
    jobrunner = FakeXTBJobRunner(server=server, scratch=False)
    
    # Create the job - similar API to Gaussian/ORCA
    job = XTBSinglePointJob(
        molecule=water,
        settings=settings,
        label="water_sp",
        jobrunner=jobrunner
    )
    
    print(f"\nJob created: {job.label}")
    print(f"xTB command: xtb {job.label}.xyz {' '.join(settings.get_command_args())}")
    print(f"Input file: {job.inputfile}")
    print(f"Output file: {job.outputfile}")
    
    # Run the job
    job.run()
    print("\n✓ Job completed successfully")
    
    # Parse results
    output = job._output()
    if output:
        print(f"\nResults:")
        print(f"  Energy: {output.energy} Eh")
        print(f"  Normal termination: {output.normal_termination}")
    print()


def example_2_geometry_optimization():
    """Example 2: Geometry optimization."""
    print("=" * 60)
    print("Example 2: Geometry Optimization")
    print("=" * 60)
    
    # Create a methane molecule
    methane = Molecule(
        symbols=['C', 'H', 'H', 'H', 'H'],
        positions=[
            [0.0, 0.0, 0.0],
            [0.63, 0.63, 0.63],
            [-0.63, -0.63, 0.63],
            [-0.63, 0.63, -0.63],
            [0.63, -0.63, -0.63]
        ]
    )
    
    # Create optimization settings
    settings = XTBJobSettings(
        method="GFN2-xTB",
        job_type="opt",
        optimization_level="tight"
    )
    
    server = Server(
        name='local',
        scheduler='LOCAL',
        queue_name='local',
        num_hours=1,
        mem_gb=2,
        num_cores=1,
        num_gpus=0
    )
    
    jobrunner = FakeXTBJobRunner(server=server, scratch=False)
    
    # Create optimization job
    job = XTBOptJob(
        molecule=methane,
        settings=settings,
        label="methane_opt",
        jobrunner=jobrunner
    )
    
    print(f"\nJob created: {job.label}")
    print(f"xTB command: xtb {job.label}.xyz {' '.join(settings.get_command_args())}")
    
    job.run()
    print("\n✓ Optimization completed")
    
    # Get optimized geometry
    output = job._output()
    if output and output.optimized_geometry:
        print(f"\nOptimized geometry:")
        print(f"  Atoms: {len(output.optimized_geometry)}")
        print(f"  Final energy: {output.energy} Eh")
        print(f"  Converged: {output.optimization_converged}")
    print()


def example_3_solvated_calculation():
    """Example 3: Calculation in implicit solvent."""
    print("=" * 60)
    print("Example 3: Solvated Calculation")
    print("=" * 60)
    
    # Create an acetate ion
    acetate = Molecule(
        symbols=['C', 'C', 'O', 'O', 'H', 'H', 'H'],
        positions=[
            [0.0, 0.0, 0.0],
            [1.5, 0.0, 0.0],
            [2.1, 1.1, 0.0],
            [2.1, -1.1, 0.0],
            [-0.5, 0.9, 0.0],
            [-0.5, -0.45, 0.87],
            [-0.5, -0.45, -0.87]
        ]
    )
    
    # Create settings with GBSA water solvation
    settings = XTBJobSettings(
        method="GFN2-xTB",
        job_type="sp",
        charge=-1,
        multiplicity=1,
        solvent_model="gbsa",
        solvent_id="water"
    )
    
    server = Server(
        name='local',
        scheduler='LOCAL',
        queue_name='local',
        num_hours=1,
        mem_gb=2,
        num_cores=1,
        num_gpus=0
    )
    
    jobrunner = FakeXTBJobRunner(server=server, scratch=False)
    
    job = XTBJob(
        molecule=acetate,
        settings=settings,
        label="acetate_water",
        jobrunner=jobrunner
    )
    
    print(f"\nJob created: {job.label}")
    print(f"xTB command: xtb {job.label}.xyz {' '.join(settings.get_command_args())}")
    print(f"Charge: {settings.charge}")
    print(f"Solvent: {settings.solvent_model}/{settings.solvent_id}")
    
    job.run()
    print("\n✓ Solvated calculation completed")
    print()


def example_4_from_file():
    """Example 4: Create job from XYZ file."""
    print("=" * 60)
    print("Example 4: Job from XYZ File")
    print("=" * 60)
    
    # Create a temporary XYZ file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', delete=False) as f:
        f.write("""3
water molecule
O     0.00000000    0.00000000    0.11779800
H     0.75695300    0.00000000   -0.47119200
H    -0.75695300    0.00000000   -0.47119200
""")
        xyz_file = f.name
    
    try:
        # Create settings
        settings = XTBJobSettings(method="GFN1-xTB", job_type="opt")
        
        server = Server(
            name='local',
            scheduler='LOCAL',
            queue_name='local',
            num_hours=1,
            mem_gb=2,
            num_cores=1,
            num_gpus=0
        )
        
        jobrunner = FakeXTBJobRunner(server=server, scratch=False)
        
        # Create job from file - similar to Gaussian/ORCA
        job = XTBJob.from_filename(
            filename=xyz_file,
            settings=settings,
            jobrunner=jobrunner
        )
        
        print(f"\nJob created from file: {xyz_file}")
        print(f"Molecule: {len(job.molecule)} atoms")
        print(f"xTB command: xtb {job.label}.xyz {' '.join(settings.get_command_args())}")
        
        job.run()
        print("\n✓ Job completed")
    finally:
        # Clean up temporary file
        os.unlink(xyz_file)
    print()


def example_5_executable_detection():
    """Example 5: Automatic executable detection."""
    print("=" * 60)
    print("Example 5: Executable Auto-detection")
    print("=" * 60)
    
    # Try to detect xTB automatically
    try:
        exe = XTBExecutable(auto_detect=True)
        xtb_path = exe.get_executable()
        print(f"\n✓ xTB automatically detected at: {xtb_path}")
    except FileNotFoundError:
        print("\n⚠ xTB not found in PATH")
        print("  You can install xTB or configure it in your server YAML file")
    print()


def main():
    """Run all examples."""
    print("\n")
    print("=" * 60)
    print("xTB Module Usage Examples")
    print("=" * 60)
    print()
    
    example_1_basic_single_point()
    example_2_geometry_optimization()
    example_3_solvated_calculation()
    example_4_from_file()
    example_5_executable_detection()
    
    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
