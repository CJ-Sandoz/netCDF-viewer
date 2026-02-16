# Packaging and distribution for netCDF-viewer

This document describes how to build a **Windows executable** with PyInstaller and how to transfer it to another user. The app includes a **runtime self-check** at startup so a broken or incomplete bundle fails gracefully with a clear message instead of a crash.

## Build (PyInstaller)

### Prerequisites

- Windows (build must be on Windows for a Windows exe).
- Python 3.10+ with the project’s **runtime** dependencies installed (so PyInstaller can trace them).

Install runtime + dev dependencies from the project root:

```powershell
cd C:\GitHub\netCDF-viewer
pip install -r requirements-dev.txt
```

This installs `ncompare`, `PySide6`, and `pyinstaller`.

### Build command (PowerShell)

From the **project root** (`C:\GitHub\netCDF-viewer`):

```powershell
pyinstaller --noconfirm --onefile --windowed --name netcdf-viewer run_netcdf_viewer.py
```

- **`--onefile`** — Single executable (no separate folder of DLLs).
- **`--windowed`** — No console window (GUI app only).
- **`--name netcdf-viewer`** — Output executable name.
- **`run_netcdf_viewer.py`** — Launcher script that imports `netcdf_viewer.app:main`; PyInstaller traces from here and pulls in the whole package and its dependencies.

### Output location

- **Executable:** `dist\netcdf-viewer.exe`
- Build artifacts (spec, build dir) are under `build\` and the generated `.spec` in the project root; you can delete `build\` and the `.spec` after testing, or keep the spec to tweak future builds.

### If the exe fails to start or misses DLLs

- **PySide6:** If Qt plugins or platforms are missing, add to the build:
  `--collect-all PySide6`
- **ncompare / netCDF4 / h5py:** If you see “module not found” or DLL errors at runtime, add hidden imports, for example:
  `--hidden-import ncompare --hidden-import netCDF4 --hidden-import h5py --hidden-import xarray`
- Then rebuild with the same command plus these options, or put them into a custom `.spec` file and run `pyinstaller netcdf-viewer.spec`.

---

## Transferring to another Windows user

1. **Build** the exe as above so that `dist\netcdf-viewer.exe` exists.
2. **Share** only that file (e.g. via USB, network share, or download link). The other user does **not** need:
   - Python installed
   - pip or any packages
   - Any other files from the repo (no config files required)
3. **Run:** The user double-clicks `netcdf-viewer.exe` or runs it from a command prompt. No installation step is required.
4. **If the runtime is broken** (e.g. incomplete bundle, missing DLL), the app shows a dialog: *“The application runtime is broken and cannot start…”* and exits. There is no traceback; details are written to `netcdf_viewer.log` next to the exe (or in the exe’s working directory when run as onefile).

---

## Principles (unchanged)

- **Non-destructive:** The app only reads netCDF/HDF5 files; it never modifies them.
- **No network in self-check:** The startup runtime check only validates local imports and Python version; it does not contact the network or read external config.
- **Single exe:** One-file build keeps distribution simple; if antivirus or startup time is an issue, you can switch to `--onedir` and share the whole `dist\netcdf-viewer\` folder instead.

---

## Entry point and launcher

- **Logical entry point:** `netcdf_viewer.app:main`
- **Build entry script:** `run_netcdf_viewer.py` (in repo root) imports and calls `main()`. PyInstaller is run against this script so that the `netcdf_viewer` package and all dependencies are collected correctly.

## Notes for ncompare and PySide6

- **ncompare** brings in netCDF4, xarray, h5py, numpy, etc. PyInstaller’s automatic analysis usually picks these up when tracing from `run_netcdf_viewer.py`. If the exe fails with a missing module or native library, add the relevant `--hidden-import` or `--collect-submodules` for that package.
- **PySide6** ships Qt libraries and plugins. For a windowed app, platform plugins (e.g. for Windows) must be in the bundle; `--collect-all PySide6` ensures Qt plugins and data files are included if the default trace is insufficient.
