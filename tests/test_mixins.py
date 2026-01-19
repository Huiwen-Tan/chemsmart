import os

from chemsmart.utils.mixins import (
    FileMixin,
    FolderMixin,
    GaussianFileMixin,
    ORCAFileMixin,
    RegistryMixin,
)


class DummyFile(FileMixin):
    def __init__(self, filename):
        self.filename = filename
        self.forces = None
        self.energies = [1.0, 2.0]
        self.input_coordinates_block = None


class TestFileMixin:
    def test_file_properties(self, temp_text_file):
        dummy = DummyFile(temp_text_file)
        assert os.path.abspath(temp_text_file) == dummy.filepath
        assert (
            os.path.basename(temp_text_file)
            == dummy.base_filename_with_extension
        )
        assert (
            dummy.basename
            == os.path.splitext(os.path.basename(temp_text_file))[0]
        )
        assert dummy.contents == ["Line1", "Line2"]
        assert dummy.content_lines_string == "Line1\nLine2\n"
        assert dummy.forces_in_eV_per_angstrom == [None, None]
        assert dummy.input_translation_vectors == []
        assert dummy.num_energies == 2


class DummyGaussianFile(GaussianFileMixin):
    def __init__(self, filename):
        self.filename = filename
        self._route_string = "modred"

    @property
    def contents(self):
        return [
            "%chk=test.chk",
            "%mem=32GB",
            "%nproc=8",
            "#p opt freq",
            "modred",
        ]

    @property
    def route_string(self):
        return self._route_string

    @property
    def modredundant_group(self):
        return ["F 1 2 3", "S 1 2 10 0.05"]


class TestGaussianFileMixin:
    def test_gaussian_file_properties(self):
        dummy = DummyGaussianFile("test.gjf")
        assert dummy.chk is True
        assert dummy._get_mem() == 32
        assert dummy._get_nproc() == 8


class DummyORCAFile(ORCAFileMixin):
    def __init__(self, filename):
        self.filename = filename

    @property
    def contents(self):
        return [
            "%mdci",
            "  cutoff 1e-5",
            "  density 1e-6",
            "%cpcm",
            "  smd true",
            '  solvent "water"',
        ]

    @property
    def route_string(self):
        return "! B3LYP def2-SVP"


class TestORCAFileMixin:
    def test_orca_file_properties(self):
        dummy = DummyORCAFile("test.inp")
        assert dummy.mdci_cutoff == "1e-5"
        assert dummy.mdci_density == "1e-6"
        assert dummy.solvent_model == "smd"
        assert dummy.solvent_id == "water"


class TestYAMLFileMixin:
    def test_yaml_file_properties(self, dummy_yaml_file):
        dummy = dummy_yaml_file
        assert dummy.yaml_contents_dict == {"key1": "value1", "key2": "value2"}
        assert "key1" in dummy.yaml_contents_keys
        assert "value1" in dummy.yaml_contents_values
        assert dummy.yaml_contents_by_key("key1") == "value1"


class BaseRegistry(RegistryMixin):
    pass


class SubRegistry1(BaseRegistry):
    pass


class SubRegistry2(BaseRegistry):
    pass


class TestRegistryMixin:
    def test_subclasses(self):
        subclasses = BaseRegistry.subclasses()
        assert SubRegistry1 in subclasses
        assert SubRegistry2 in subclasses


class DummyFolder(FolderMixin):
    def __init__(self, folder):
        self.folder = folder


class TestFolderMixin:
    def test_get_all_files_by_suffix(self, temp_folder_with_files):
        folder, file1, file2 = temp_folder_with_files
        dummy = DummyFolder(folder)
        txt_files = dummy.get_all_files_in_current_folder_by_suffix(".txt")
        assert file1 in txt_files

    def test_get_all_files_by_regex(self, temp_folder_with_files):
        folder, file1, file2 = temp_folder_with_files
        dummy = DummyFolder(folder)
        log_files = dummy.get_all_files_in_current_folder_matching_regex(
            r".*\.log"
        )
        assert file2 in log_files
        assert file1 not in log_files


class TestGaussianOutputFMOProperties:
    """Test FMO-related properties from FileMixin with Gaussian output files."""

    def test_gaussian_singlet_fmo_properties(
        self, gaussian_singlet_opt_outfile
    ):
        """Test FMO properties for closed-shell (singlet) system."""
        from chemsmart.io.gaussian.output import Gaussian16Output

        g = Gaussian16Output(gaussian_singlet_opt_outfile)

        # Test multiplicity and unpaired electrons
        assert g.multiplicity == 1
        assert g.num_unpaired_electrons == 0

        # Test SOMO properties (should be None for singlet)
        assert g.somo_energies is None
        assert g.lowest_somo_energy is None
        assert g.highest_somo_energy is None

        # Test HOMO/LUMO energies
        assert g.homo_energy is not None
        assert g.lumo_energy is not None
        assert g.alpha_homo_energy is not None
        assert g.alpha_lumo_energy is not None

        # Test FMO gap
        assert g.fmo_gap is not None
        assert g.fmo_gap > 0
        assert g.alpha_fmo_gap is not None

    def test_gaussian_triplet_fmo_properties(
        self, gaussian_triplet_opt_outfile
    ):
        """Test FMO properties for open-shell (triplet) system."""
        from chemsmart.io.gaussian.output import Gaussian16Output

        g = Gaussian16Output(gaussian_triplet_opt_outfile)

        # Test multiplicity and unpaired electrons
        assert g.multiplicity == 3
        assert g.num_unpaired_electrons == 2

        # Test SOMO properties (should exist for triplet)
        assert g.somo_energies is not None
        assert len(g.somo_energies) == 2
        assert g.lowest_somo_energy is not None
        assert g.highest_somo_energy is not None
        assert g.lowest_somo_energy <= g.highest_somo_energy

        # Test alpha/beta HOMO/LUMO energies
        assert g.alpha_homo_energy is not None
        assert g.beta_homo_energy is not None
        assert g.alpha_lumo_energy is not None
        assert g.beta_lumo_energy is not None

        # Test that homo_energy and lumo_energy are None for open-shell
        assert g.homo_energy is None
        assert g.lumo_energy is None

        # Test FMO gaps
        assert g.fmo_gap is not None
        assert g.alpha_fmo_gap is not None
        assert g.beta_fmo_gap is not None

    def test_gaussian_quintet_fmo_properties(
        self, gaussian_quintet_opt_outfile
    ):
        """Test FMO properties for open-shell (quintet) system."""
        from chemsmart.io.gaussian.output import Gaussian16Output

        g = Gaussian16Output(gaussian_quintet_opt_outfile)

        # Test multiplicity and unpaired electrons
        assert g.multiplicity == 5
        assert g.num_unpaired_electrons == 4

        # Test SOMO properties (should exist for quintet)
        assert g.somo_energies is not None
        assert len(g.somo_energies) == 4
        assert g.lowest_somo_energy is not None
        assert g.highest_somo_energy is not None

        # Test that SOMO energies are ordered
        somo = g.somo_energies
        for i in range(len(somo) - 1):
            assert somo[i] <= somo[i + 1]


class TestORCAOutputFMOProperties:
    """Test FMO-related properties from FileMixin with ORCA output files."""

    def test_orca_singlet_fmo_properties(self, fe2_singlet_output):
        """Test FMO properties for closed-shell (singlet) system."""
        from chemsmart.io.orca.output import ORCAOutput

        o = ORCAOutput(fe2_singlet_output)

        # Test multiplicity and unpaired electrons
        assert o.multiplicity == 1
        assert o.num_unpaired_electrons == 0

        # Test SOMO properties (should be None for singlet)
        assert o.somo_energies is None
        assert o.lowest_somo_energy is None
        assert o.highest_somo_energy is None

        # Test HOMO/LUMO energies
        assert o.homo_energy is not None
        assert o.lumo_energy is not None
        assert o.alpha_homo_energy is not None
        assert o.alpha_lumo_energy is not None

        # Test FMO gap
        assert o.fmo_gap is not None
        assert o.fmo_gap > 0
        assert o.alpha_fmo_gap is not None

    def test_orca_triplet_fmo_properties(self, fe2_triplet_output):
        """Test FMO properties for open-shell (triplet) system."""
        from chemsmart.io.orca.output import ORCAOutput

        o = ORCAOutput(fe2_triplet_output)

        # Test multiplicity and unpaired electrons
        assert o.multiplicity == 3
        assert o.num_unpaired_electrons == 2

        # Test SOMO properties (should exist for triplet)
        assert o.somo_energies is not None
        assert len(o.somo_energies) == 2
        assert o.lowest_somo_energy is not None
        assert o.highest_somo_energy is not None
        assert o.lowest_somo_energy <= o.highest_somo_energy

        # Test alpha/beta HOMO/LUMO energies
        assert o.alpha_homo_energy is not None
        assert o.beta_homo_energy is not None
        assert o.alpha_lumo_energy is not None
        assert o.beta_lumo_energy is not None

        # Test that homo_energy and lumo_energy are None for open-shell
        assert o.homo_energy is None
        assert o.lumo_energy is None

        # Test FMO gaps
        assert o.fmo_gap is not None
        assert o.alpha_fmo_gap is not None
        assert o.beta_fmo_gap is not None

    def test_orca_quintet_fmo_properties(self, fe2_quintet_output):
        """Test FMO properties for open-shell (quintet) system."""
        from chemsmart.io.orca.output import ORCAOutput

        o = ORCAOutput(fe2_quintet_output)

        # Test multiplicity and unpaired electrons
        assert o.multiplicity == 5
        assert o.num_unpaired_electrons == 4

        # Test SOMO properties (should exist for quintet)
        assert o.somo_energies is not None
        assert len(o.somo_energies) == 4
        assert o.lowest_somo_energy is not None
        assert o.highest_somo_energy is not None

        # Test that SOMO energies are ordered
        somo = o.somo_energies
        for i in range(len(somo) - 1):
            assert somo[i] <= somo[i + 1]

    def test_orca_doublet_fmo_properties(self, fe3_doublet_output):
        """Test FMO properties for open-shell (doublet) system."""
        from chemsmart.io.orca.output import ORCAOutput

        o = ORCAOutput(fe3_doublet_output)

        # Test multiplicity and unpaired electrons
        assert o.multiplicity == 2
        assert o.num_unpaired_electrons == 1

        # Test SOMO properties (should exist for doublet)
        assert o.somo_energies is not None
        assert len(o.somo_energies) == 1
        assert o.lowest_somo_energy is not None
        assert o.highest_somo_energy is not None
        assert o.lowest_somo_energy == o.highest_somo_energy

    def test_orca_quartet_fmo_properties(self, fe3_quartet_output):
        """Test FMO properties for open-shell (quartet) system."""
        from chemsmart.io.orca.output import ORCAOutput

        o = ORCAOutput(fe3_quartet_output)

        # Test multiplicity and unpaired electrons
        assert o.multiplicity == 4
        assert o.num_unpaired_electrons == 3

        # Test SOMO properties (should exist for quartet)
        assert o.somo_energies is not None
        assert len(o.somo_energies) == 3

    def test_orca_sextet_fmo_properties(self, fe3_sextet_output):
        """Test FMO properties for open-shell (sextet) system."""
        from chemsmart.io.orca.output import ORCAOutput

        o = ORCAOutput(fe3_sextet_output)

        # Test multiplicity and unpaired electrons
        assert o.multiplicity == 6
        assert o.num_unpaired_electrons == 5

        # Test SOMO properties (should exist for sextet)
        assert o.somo_energies is not None
        assert len(o.somo_energies) == 5
