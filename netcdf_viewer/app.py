"""GUI entry point for netCDF-viewer.

Runtime self-check runs before the main window: it verifies Python version
and that ncompare and PySide6 are importable (works from source and from
a PyInstaller-built executable). On failure, a user-friendly error is
shown and the app exits cleanly.

To build a standalone Windows executable (from project root in PowerShell):
    pip install -r requirements-dev.txt
    pyinstaller --noconfirm --onefile --windowed --name netcdf-viewer run_netcdf_viewer.py

Output: dist\\netcdf-viewer.exe . Share that single file with another
Windows user; they run it without installing Python or any dependencies.
"""

import logging
import sys
from pathlib import Path

# Do not import netcdf_viewer.gui or PySide6 at module level so that
# _check_runtime() can run first and show a clean error if dependencies are missing.


def _setup_logging() -> None:
    """Log unexpected exceptions to a file in the project or cwd."""
    log_path = Path(__file__).resolve().parent.parent / "netcdf_viewer.log"
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    logging.getLogger("netcdf_viewer").setLevel(logging.DEBUG)


def _check_runtime(logger: logging.Logger) -> None:
    """Verify the bundled runtime: Python version and required packages.

    Validates local state only (no network, no external config). On failure:
    log details, show a user-friendly error dialog, and exit cleanly.
    Works from source (python -m netcdf_viewer.app) and from a PyInstaller exe.
    """
    errors: list[str] = []
    min_py = (3, 10)

    if sys.version_info < min_py:
        msg = (
            f"Python {min_py[0]}.{min_py[1]} or newer is required; "
            f"found {sys.version_info.major}.{sys.version_info.minor}."
        )
        errors.append(msg)
        logger.error(msg)

    try:
        import ncompare  # noqa: F401
    except Exception as e:
        errors.append(f"ncompare: {e}")
        logger.exception("ncompare import failed")

    try:
        from PySide6.QtWidgets import QApplication  # noqa: F401
    except Exception as e:
        errors.append(f"PySide6: {e}")
        logger.exception("PySide6 import failed")

    if not errors:
        return

    full_msg = (
        "The application runtime is broken and cannot start.\n\n"
        + "\n".join(errors)
        + "\n\nPlease reinstall or rebuild the application."
    )
    logger.error("Runtime check failed: %s", full_msg)

    # Show error: use Qt if available (e.g. only ncompare failed), else Windows MessageBox
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication(sys.argv)
        QMessageBox.critical(None, "netCDF-viewer — Startup Error", full_msg)
    except Exception:
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    None,
                    full_msg,
                    "netCDF-viewer — Startup Error",
                    0x10,  # MB_ICONERROR
                )
            except Exception as fallback_err:
                logger.exception("Could not show error dialog: %s", fallback_err)
                print(full_msg, file=sys.stderr)
        else:
            print(full_msg, file=sys.stderr)
    sys.exit(1)


def main() -> None:
    """Launch the netCDF-viewer desktop application."""
    _setup_logging()
    logger = logging.getLogger("netcdf_viewer.app")
    _check_runtime(logger)

    from PySide6.QtWidgets import QApplication
    from netcdf_viewer.gui.main_window import MainWindow

    try:
        app = QApplication(sys.argv)
        app.setApplicationName("netCDF-viewer")
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logger.exception("Unexpected error at startup: %s", e)
        raise


if __name__ == "__main__":
    main()
