import os
import sys

def _set_cwd_to_exe_dir() -> None:
    # At PyInstaller runtime, switch the working directory to the executable's directory
    try:
        if hasattr(sys, "_MEIPASS"):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        os.chdir(base_dir)
    except Exception:
        # Keep the default working directory
        pass

_set_cwd_to_exe_dir()


