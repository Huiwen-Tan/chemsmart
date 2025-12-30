"""
xTB executable configuration.

This module provides the XTBExecutable class for managing xTB program
executable paths and environment configurations. It supports automatic
detection of xTB in the system PATH.
"""

import logging
import os
import shutil

from chemsmart.settings.executable import Executable

logger = logging.getLogger(__name__)


class XTBExecutable(Executable):
    """
    xTB executable configuration and management.

    This class handles xTB executable path detection and configuration.
    It can auto-detect xTB from the system PATH or use configurations
    from server YAML files.

    Attributes:
        PROGRAM (str): Program identifier ('xtb').
        executable_folder (str): Path to xTB executable directory.
        local_run (bool): Whether to run locally.
        conda_env (str): Conda environment configuration.
        modules (str): Module loading commands.
        scripts (str): Additional script commands.
        envars (str): Environment variable export commands.
    """

    PROGRAM = "xtb"

    def __init__(
        self,
        executable_folder=None,
        local_run=True,
        conda_env=None,
        modules=None,
        scripts=None,
        envars=None,
        auto_detect=True,
    ):
        """
        Initialize the xTB executable instance.

        Args:
            executable_folder (str, optional): Path to xTB executable directory.
            local_run (bool): Whether to run locally. Defaults to True.
            conda_env (str, optional): Conda environment configuration.
            modules (str, optional): Module loading commands.
            scripts (str, optional): Additional script commands.
            envars (str, optional): Environment variable export commands.
            auto_detect (bool): Whether to auto-detect xTB in PATH. Defaults to True.
        """
        # Try auto-detection if enabled and no folder specified
        if auto_detect and executable_folder is None:
            detected_path = self._auto_detect_xtb()
            if detected_path:
                executable_folder = os.path.dirname(detected_path)
                logger.info(f"Auto-detected xTB at: {detected_path}")

        super().__init__(
            executable_folder=executable_folder,
            local_run=local_run,
            conda_env=conda_env,
            modules=modules,
            scripts=scripts,
            envars=envars,
        )

    @staticmethod
    def _auto_detect_xtb():
        """
        Auto-detect xTB executable in system PATH.

        Returns:
            str or None: Full path to xTB executable if found, None otherwise.
        """
        xtb_path = shutil.which("xtb")
        if xtb_path:
            logger.debug(f"Found xTB executable in PATH: {xtb_path}")
            return xtb_path
        else:
            logger.debug("xTB executable not found in PATH")
            return None

    def get_executable(self):
        """
        Get the full path to the xTB executable.

        Returns:
            str: Full path to xTB executable.

        Raises:
            FileNotFoundError: If xTB executable cannot be found.
        """
        # First try the configured executable folder
        if self.executable_folder:
            xtb_exe = os.path.join(self.executable_folder, "xtb")
            if os.path.exists(xtb_exe):
                return xtb_exe
            # Also check if the folder IS the executable
            if os.path.isfile(self.executable_folder) and os.access(
                self.executable_folder, os.X_OK
            ):
                return self.executable_folder

        # Try auto-detection as fallback
        xtb_path = self._auto_detect_xtb()
        if xtb_path:
            return xtb_path

        # If still not found, raise error
        raise FileNotFoundError(
            "xTB executable not found. Please install xTB or configure "
            "the executable path in your server YAML file."
        )

    @classmethod
    def from_servername(cls, servername):
        """
        Create an XTBExecutable instance from server configuration file.

        If xTB is not configured in the server file, attempts auto-detection.

        Args:
            servername (str): Name of the server configuration file.

        Returns:
            XTBExecutable: An instance configured with server-specific settings.
        """
        try:
            # Try to get configuration from server file
            return super().from_servername(servername)
        except (KeyError, FileNotFoundError) as e:
            # If xTB is not in the server file, use auto-detection
            logger.info(
                f"xTB not configured in server file ({e}), "
                "attempting auto-detection"
            )
            return cls(auto_detect=True)
