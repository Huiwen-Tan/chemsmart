import logging
import os

from chemsmart.io.folder import BaseFolder
from chemsmart.utils.io import get_outfile_format

logger = logging.getLogger(__name__)


class XTBFolder(BaseFolder):
    """
    Folder containing all XTB-related output files for postprocessing.
    """

    def __init__(self, folder):
        """
        Initialize XTB output folder handler.

        Args:
            folder (str): Parent folder for all output files
        """
        self.folder = folder

    def _xtb_out(self):
        """Return the path to the main XTB output file."""
        outfiles = self.get_all_files_in_current_folder_by_suffix(".out")
        for outfile in outfiles:
            # Check if it's an XTB output file
            if get_outfile_format(outfile) == "xtb":
                return outfile
        # If no XTB-specific file found, return first .out file
        return outfiles[0] if outfiles else None

    def _xtb_err(self):
        """Return path to XTB error output file."""
        errfiles = self.get_all_files_in_current_folder_by_suffix(".err")
        return errfiles[0] if errfiles else None

    def _charge(self):
        """Return path to charge file."""
        charge_file = os.path.join(self.folder, "charges")
        return charge_file if os.path.exists(charge_file) else None

    def _xtbopt_log(self):
        """Return path to xtbopt.log (optimization trajectory)."""
        xtbopt_log = os.path.join(self.folder, "xtbopt.log")
        return xtbopt_log if os.path.exists(xtbopt_log) else None

    def _xtbopt_xyz(self):
        """Return path to xtbopt.xyz (optimized structure)."""
        xtbopt_xyz = os.path.join(self.folder, "xtbopt.xyz")
        return xtbopt_xyz if os.path.exists(xtbopt_xyz) else None
    
    def _xtbopt_coord(self):
        """Return path to xtbopt.coord (optimized structure in coord format)."""
        xtbopt_coord = os.path.join(self.folder, "xtbopt.coord")
        return xtbopt_coord if os.path.exists(xtbopt_coord) else None

    def _gradient(self):
        """Return path to gradient file."""
        gradient_file = os.path.join(self.folder, "gradient")
        return gradient_file if os.path.exists(gradient_file) else None
    
    def _hessian(self):
        """Return path to hessian file."""
        hessian_file = os.path.join(self.folder, "hessian")
        return hessian_file if os.path.exists(hessian_file) else None
    
    def _wbo(self):
        """Return path to Wiberg bond order file."""
        wbo_file = os.path.join(self.folder, "wbo")
        return wbo_file if os.path.exists(wbo_file) else None
    
    def _xtbrestart(self):
        """Return path to restart file."""
        restart_file = os.path.join(self.folder, "xtbrestart")
        return restart_file if os.path.exists(restart_file) else None
    
    def has_xtb_output(self):
        """Check if main XTB output file exists."""
        return self._xtb_out() is not None
    
    def has_optimization_trajectory(self):
        """Check if optimization trajectory file exists."""
        return self._xtbopt_log() is not None
    
    def has_optimized_structure(self):
        """Check if optimized structure file exists."""
        return self._xtbopt_xyz() is not None or self._xtbopt_coord() is not None
    
    def has_gradient(self):
        """Check if gradient file exists."""
        return self._gradient() is not None
    
    def has_hessian(self):
        """Check if hessian file exists."""
        return self._hessian() is not None
