"""
Tests for xTB job functionality.

This module tests the xTB job classes, settings, and runners.
"""

import os
import tempfile

import ase
import pytest
from ase import Atoms

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chemsmart.jobs.xtb import XTBJob, XTBOptJob, XTBSinglePointJob, XTBJobRunner
from chemsmart.settings.xtb import XTBJobSettings
from chemsmart.io.xtb.output import XTBOutput
from chemsmart.io.molecules.structure import Molecule


class TestXTBJobSettings:
    """Test XTBJobSettings class."""

    def test_default_settings(self):
        """Test creation of default settings."""
        settings = XTBJobSettings.default()
        assert settings.method == "GFN2-xTB"
        assert settings.charge == 0
        assert settings.multiplicity == 1
        assert settings.task == "sp"

    def test_custom_settings(self):
        """Test custom settings creation."""
        settings = XTBJobSettings(
            method="GFN1-xTB",
            charge=1,
            multiplicity=2,
            task="opt",
            solvent="water",
        )
        assert settings.method == "GFN1-xTB"
        assert settings.charge == 1
        assert settings.multiplicity == 2
        assert settings.task == "opt"
        assert settings.solvent == "water"

    def test_method_flags(self):
        """Test method flag generation."""
        settings_gfn2 = XTBJobSettings(method="GFN2-xTB")
        assert settings_gfn2.get_method_flag() == "--gfn 2"

        settings_gfn1 = XTBJobSettings(method="GFN1-xTB")
        assert settings_gfn1.get_method_flag() == "--gfn 1"

        settings_gfnff = XTBJobSettings(method="GFN-FF")
        assert settings_gfnff.get_method_flag() == "--gfnff"

    def test_task_flags(self):
        """Test task flag generation."""
        settings_sp = XTBJobSettings(task="sp")
        assert settings_sp.get_task_flag() == ""

        settings_opt = XTBJobSettings(task="opt")
        assert settings_opt.get_task_flag() == "--opt"

        settings_hess = XTBJobSettings(task="hess")
        assert settings_hess.get_task_flag() == "--hess"

    def test_command_building(self):
        """Test complete command argument building."""
        settings = XTBJobSettings(
            method="GFN2-xTB",
            task="opt",
            charge=0,
            multiplicity=1,
        )
        args = settings.build_command_args("test.xyz")

        assert "test.xyz" in args
        assert "--opt" in args
        assert "--gfn" in args
        assert "2" in args
        assert "--chrg" in args
        assert "0" in args

    def test_command_with_solvent(self):
        """Test command building with solvent."""
        settings = XTBJobSettings(
            method="GFN2-xTB",
            task="sp",
            charge=0,
            multiplicity=1,
            solvent="water",
        )
        args = settings.build_command_args("test.xyz")

        assert "--alpb" in args
        assert "water" in args

    def test_command_with_unpaired_electrons(self):
        """Test command building with unpaired electrons."""
        settings = XTBJobSettings(
            method="GFN2-xTB",
            task="sp",
            charge=0,
            multiplicity=3,  # 2 unpaired electrons
        )
        args = settings.build_command_args("test.xyz")

        assert "--uhf" in args
        assert "2" in args  # multiplicity - 1


class TestXTBJob:
    """Test XTBJob class."""

    def test_job_creation(self):
        """Test basic job creation."""
        water = Atoms('H2O', positions=[[0, 0, 0], [0.96, 0, 0], [0.24, 0.93, 0]])
        molecule = Molecule.from_ase_atoms(water)

        settings = XTBJobSettings.default()
        job = XTBJob(molecule=molecule, settings=settings, label="test_water")

        assert job.molecule is not None
        assert job.settings is not None
        assert job.label == "test_water"
        assert job.PROGRAM == "XTB"

    def test_job_file_paths(self):
        """Test job file path generation."""
        water = Atoms('H2O', positions=[[0, 0, 0], [0.96, 0, 0], [0.24, 0.93, 0]])
        molecule = Molecule.from_ase_atoms(water)

        settings = XTBJobSettings.default()
        job = XTBJob(molecule=molecule, settings=settings, label="test_water")

        assert job.inputfile.endswith("test_water.xyz")
        assert job.outputfile.endswith("test_water.out")
        assert job.errfile.endswith("test_water.err")


class TestXTBSinglePointJob:
    """Test XTBSinglePointJob class."""

    def test_sp_job_creation(self):
        """Test single point job creation."""
        water = Atoms('H2O', positions=[[0, 0, 0], [0.96, 0, 0], [0.24, 0.93, 0]])
        molecule = Molecule.from_ase_atoms(water)

        job = XTBSinglePointJob(molecule=molecule, label="test_sp")

        assert job.TYPE == "xtbsp"
        assert job.settings.task == "sp"


class TestXTBOptJob:
    """Test XTBOptJob class."""

    def test_opt_job_creation(self):
        """Test optimization job creation."""
        water = Atoms('H2O', positions=[[0, 0, 0], [0.96, 0, 0], [0.24, 0.93, 0]])
        molecule = Molecule.from_ase_atoms(water)

        job = XTBOptJob(molecule=molecule, label="test_opt")

        assert job.TYPE == "xtbopt"
        assert job.settings.task == "opt"


class TestXTBJobRunner:
    """Test XTBJobRunner class."""

    def test_runner_jobtypes(self):
        """Test runner job types."""
        assert "xtbsp" in XTBJobRunner.JOBTYPES
        assert "xtbopt" in XTBJobRunner.JOBTYPES
        assert XTBJobRunner.PROGRAM == "xtb"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
