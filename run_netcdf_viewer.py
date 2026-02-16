"""Launcher script for netCDF-viewer.

Used by PyInstaller: run from project root so the netcdf_viewer package
is on the path. Do not add package logic here; all behavior is in netcdf_viewer.app.
"""

if __name__ == "__main__":
    from netcdf_viewer.app import main
    main()
