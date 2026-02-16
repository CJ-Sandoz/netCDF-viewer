# netCDF-viewer Architecture

## Purpose

**netCDF-viewer** is a standalone Windows desktop application for pre-ingestion inspection of scientific data. It compares the **structure, variables, and metadata** of two netCDF (or HDF5) files using the NASA [ncompare](https://github.com/nasa/ncompare) Python package. The app does **not** perform full data-value diffing; it focuses on:

- Groups and variables (names, types, shapes, chunking)
- Dimensions and their lengths
- Global and variable-level attributes
- Matching vs non-matching structure to support human-in-the-loop decisions for later ingestion

The tool is **non-destructive** (read-only), **transparent** (all ncompare options visible in the UI), and **human-in-the-loop** (no auto-accept or auto-reject).

---

## Main Components

### 1. GUI layer (`netcdf_viewer/gui/`)

- **Responsibilities:** UI layout, file selection, option controls, displaying comparison results and errors, progress feedback.
- **Key module:** `main_window.py` — main window with file A/B selectors, ncompare options (only differences, include attributes, include chunking), Compare button, summary panel, and differences panel.
- **Toolkit:** PySide6 (Qt for Python). See [GUI toolkit choice](#gui-toolkit-choice) below.

### 2. Services layer (`netcdf_viewer/services/`)

- **Responsibilities:** Call ncompare’s Python API, optionally write report files (text/CSV), and transform results into structured models. **Read-only** with respect to input files.
- **Key module:** `compare_service.py` — `run_comparison(file_a, file_b, options) -> ComparisonResult` using `ncompare.compare()` and ncompare getters for file summaries.

### 3. Models (`netcdf_viewer/models/`)

- **Responsibilities:** Data structures for comparison options and results.
- **Key module:** `comparison_result.py` — `ComparisonOptions` (only_differences, include_attributes, include_chunking, report paths) and `ComparisonResult` (per-file dimensions/variables, matching vs non-matching groups/variables/attributes, counts, optional report paths).

---

## Data flow

1. User selects File A and File B and sets options in the GUI.
2. On “Compare”, the GUI builds `ComparisonOptions` and calls the compare service (e.g. in a background thread).
3. The service calls `ncompare.compare()` with those options and optional report paths, and uses ncompare’s getters for dimensions/groups/variables to build per-file summaries.
4. The service returns a `ComparisonResult` (and report file paths if requested).
5. The GUI displays summary (dimensions, variable table with shape/count) and differences (non-matching groups/variables, attribute differences).

---

## GUI toolkit choice

**PySide6** was selected for the Windows desktop GUI because:

- **License:** LGPL — easier to ship a proprietary or mixed-license product than PyQt6 (GPL).
- **Capabilities:** Native-feeling file dialogs, robust `QTableWidget` / `QTreeWidget` for summary and differences, and good support for progress indicators and threading.
- **Platform:** First-class Windows support and a well-documented path to packaging (e.g. PyInstaller) for a single executable or installer.

---

## Entry point

- **Application entry:** `netcdf_viewer.app:main()` (e.g. `python -m netcdf_viewer.app`).
- **Packaging:** Planned as a Windows executable/installer (see `PACKAGING.md`); design keeps a single entry point and minimal side effects for packaging.
