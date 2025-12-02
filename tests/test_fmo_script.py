"""
Tests for the FMO (Frontier Molecular Orbital) analysis script.

Tests both closed-shell and open-shell systems with Gaussian and ORCA output files.
"""

from click.testing import CliRunner

from chemsmart.scripts.fmo import entry_point


class TestFMOScript:
    """Test the FMO analysis script."""

    def test_closed_shell_gaussian_default_unit(
        self, gaussian_outputs_test_directory
    ):
        """Test FMO calculation for closed-shell Gaussian system with default eV unit."""
        import os

        filename = os.path.join(gaussian_outputs_test_directory, "benzene.log")
        runner = CliRunner()
        result = runner.invoke(entry_point, ["-f", filename])

        assert result.exit_code == 0
        assert "HOMO energy:" in result.output
        assert "LUMO energy:" in result.output
        assert "HOMO-LUMO gap:" in result.output
        assert "Chemical potential, mu:" in result.output
        assert "Chemical hardness, eta:" in result.output
        assert "Electrophilicity Index, omega:" in result.output
        assert "eV" in result.output
        # Should NOT display open-shell specific info
        assert "Open-shell system detected" not in result.output
        assert "SOMO" not in result.output

    def test_closed_shell_gaussian_kcal_mol_unit(
        self, gaussian_outputs_test_directory
    ):
        """Test FMO calculation for closed-shell system with kcal/mol unit."""
        import os

        filename = os.path.join(gaussian_outputs_test_directory, "benzene.log")
        runner = CliRunner()
        result = runner.invoke(entry_point, ["-f", filename, "-u", "kcal/mol"])

        assert result.exit_code == 0
        assert "kcal/mol" in result.output

    def test_open_shell_gaussian_triplet(self, gaussian_triplet_opt_outfile):
        """Test FMO calculation for triplet (open-shell) Gaussian system."""
        runner = CliRunner()
        result = runner.invoke(entry_point, ["-f", gaussian_triplet_opt_outfile])

        assert result.exit_code == 0
        assert "Open-shell system detected" in result.output
        assert "Multiplicity: 3" in result.output
        assert "Number of unpaired electrons: 2" in result.output
        assert "Number of SOMOs: 2" in result.output
        assert "SOMO 1 energy:" in result.output
        assert "SOMO 2 energy:" in result.output
        assert "Lowest SOMO energy:" in result.output
        assert "Highest SOMO energy:" in result.output
        assert "Alpha spin channel:" in result.output
        assert "Beta spin channel:" in result.output
        assert "HOMO(alpha) energy:" in result.output
        assert "LUMO(alpha) energy:" in result.output
        assert "HOMO(beta) energy:" in result.output
        assert "LUMO(beta) energy:" in result.output
        assert "FMO gap (SOMO-LUMO):" in result.output
        assert "Chemical potential, mu:" in result.output
        assert "Chemical hardness, eta:" in result.output
        assert "Electrophilicity Index, omega:" in result.output

    def test_open_shell_gaussian_quintet(self, gaussian_quintet_opt_outfile):
        """Test FMO calculation for quintet (open-shell) Gaussian system."""
        runner = CliRunner()
        result = runner.invoke(entry_point, ["-f", gaussian_quintet_opt_outfile])

        assert result.exit_code == 0
        assert "Open-shell system detected" in result.output
        assert "Multiplicity: 5" in result.output
        assert "Number of unpaired electrons: 4" in result.output
        assert "Number of SOMOs: 4" in result.output

    def test_open_shell_gaussian_kcal_mol_unit(
        self, gaussian_triplet_opt_outfile
    ):
        """Test FMO calculation for open-shell system with kcal/mol unit."""
        runner = CliRunner()
        result = runner.invoke(
            entry_point, ["-f", gaussian_triplet_opt_outfile, "-u", "kcal/mol"]
        )

        assert result.exit_code == 0
        assert "kcal/mol" in result.output
        assert "Open-shell system detected" in result.output

    def test_closed_shell_orca(self, fe2_singlet_output):
        """Test FMO calculation for closed-shell ORCA system."""
        runner = CliRunner()
        result = runner.invoke(entry_point, ["-f", fe2_singlet_output])

        assert result.exit_code == 0
        assert "HOMO energy:" in result.output
        assert "LUMO energy:" in result.output
        # Should NOT display open-shell specific info
        assert "Open-shell system detected" not in result.output
        assert "SOMO" not in result.output

    def test_open_shell_orca_triplet(self, fe2_triplet_output):
        """Test FMO calculation for triplet (open-shell) ORCA system."""
        runner = CliRunner()
        result = runner.invoke(entry_point, ["-f", fe2_triplet_output])

        assert result.exit_code == 0
        assert "Open-shell system detected" in result.output
        assert "Multiplicity: 3" in result.output
        assert "Number of unpaired electrons: 2" in result.output
        assert "Number of SOMOs: 2" in result.output

    def test_open_shell_orca_quintet(self, fe2_quintet_output):
        """Test FMO calculation for quintet (open-shell) ORCA system."""
        runner = CliRunner()
        result = runner.invoke(entry_point, ["-f", fe2_quintet_output])

        assert result.exit_code == 0
        assert "Open-shell system detected" in result.output
        assert "Multiplicity: 5" in result.output
        assert "Number of unpaired electrons: 4" in result.output
        assert "Number of SOMOs: 4" in result.output

    def test_open_shell_orca_doublet(self, fe3_doublet_output):
        """Test FMO calculation for doublet (open-shell) ORCA system."""
        runner = CliRunner()
        result = runner.invoke(entry_point, ["-f", fe3_doublet_output])

        assert result.exit_code == 0
        assert "Open-shell system detected" in result.output
        assert "Multiplicity: 2" in result.output
        assert "Number of unpaired electrons: 1" in result.output
        assert "Number of SOMOs: 1" in result.output

    def test_unknown_filetype(self, tmp_path):
        """Test error handling for unknown file type."""
        # Create a temporary file that is not a Gaussian or ORCA output
        unknown_file = tmp_path / "unknown.txt"
        unknown_file.write_text("This is not a quantum chemistry output file")

        runner = CliRunner()
        result = runner.invoke(entry_point, ["-f", str(unknown_file)])

        assert result.exit_code != 0 or "unknown filetype" in result.output
