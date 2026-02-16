"""Service that runs ncompare and builds a ComparisonResult.

Uses the ncompare Python API (compare() and path/getter helpers). Read-only:
never modifies the input netCDF/HDF5 files. All options passed to ncompare
come from ComparisonOptions (visibility in UI).
"""

import csv
import tempfile
import uuid
from pathlib import Path

from ncompare import compare as ncompare_compare
from ncompare.path_and_string_operations import ensure_valid_path_exists, validate_file_type
from ncompare.getters import get_root_dims, get_root_groups, get_variables
from ncompare.utility_types import FileToCompare

from netcdf_viewer.models.comparison_result import ComparisonOptions, ComparisonResult


def _collect_variables_with_shapes(
    file_obj: FileToCompare,
) -> list[tuple[str, str, int]]:
    """Collect (name, shape_str, point_count) for all variables in the file.

    Uses ncompare's getters to open the file and traverse root + groups.
    Point count is the product of dimension lengths (for symmetry assessment).
    """
    import netCDF4
    import h5py

    result: list[tuple[str, str, int]] = []
    opener = netCDF4.Dataset if file_obj.type == "netcdf" else h5py.File
    with opener(file_obj.path, mode="r") as ds:
        # Root group variables
        vars_root = get_variables(ds, file_obj.type)
        for vname in vars_root:
            var = ds.variables[vname] if file_obj.type == "netcdf" else ds[vname]
            shape = getattr(var, "shape", ())
            shape_str = str(shape)
            count = 1
            for s in shape:
                count *= int(s)
            result.append((vname, shape_str, count))
        # Subgroups (recursive names only from root groups here; full traversal would need recursion)
        for gname in get_root_groups(file_obj):
            try:
                grp = ds.groups[gname] if file_obj.type == "netcdf" else ds[gname]
                subvars = get_variables(grp, file_obj.type)
                for vname in subvars:
                    var = grp.variables[vname] if file_obj.type == "netcdf" else grp[vname]
                    shape = getattr(var, "shape", ())
                    shape_str = str(shape)
                    count = 1
                    for s in shape:
                        count *= int(s)
                    result.append((f"{gname}/{vname}", shape_str, count))
            except (KeyError, TypeError):
                continue
    return result


def _dimensions_list(file_obj: FileToCompare) -> list[tuple[str, int]]:
    """Return list of (dim_name, length) from ncompare get_root_dims."""
    dims = get_root_dims(file_obj)
    # get_root_dims returns list of (name, size) from xarray dataset.sizes
    return [(str(k), int(v)) for k, v in dims]


def _parse_csv_for_summary_and_diffs(
    csv_path: Path,
) -> tuple[
    int, int, int, int, int, int, int, list[tuple[str, str, str]]
]:
    """Parse ncompare CSV output for summary counts and difference rows.

    Returns:
        variables_only_in_a, variables_only_in_b, variables_shared,
        groups_only_in_a, groups_only_in_b, groups_shared,
        attribute_difference_count (approximate from *** rows),
        difference_details list of (info, value_a, value_b).
    """
    var_left = var_right = var_shared = 0
    grp_left = grp_right = grp_shared = 0
    attr_diffs = 0
    details: list[tuple[str, str, str]] = []

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if len(row) < 3:
                continue
            info, val_a, val_b = row[0].strip(), row[1].strip(), row[2].strip()
            marker = row[3].strip() if len(row) > 3 else ""
            if marker == "***":
                details.append((info, val_a, val_b))
                if "attribute" in info.lower() or info not in ("dtype", "dimensions", "shape", "chunksize"):
                    attr_diffs += 1
            if "Total # of shared variables" in info:
                try:
                    var_shared = int(val_a) if val_a.isdigit() else int(val_b)
                except ValueError:
                    pass
            if "Total # of non-shared variables" in info:
                try:
                    var_left = int(val_a) if val_a.isdigit() else 0
                    var_right = int(val_b) if val_b.isdigit() else 0
                except ValueError:
                    pass
            if "Total # of shared groups" in info:
                try:
                    grp_shared = int(val_a) if val_a.isdigit() else int(val_b)
                except ValueError:
                    pass
            if "Total # of non-shared groups" in info:
                try:
                    grp_left = int(val_a) if val_a.isdigit() else 0
                    grp_right = int(val_b) if val_b.isdigit() else 0
                except ValueError:
                    pass

    return var_left, var_right, var_shared, grp_left, grp_right, grp_shared, len(details), details


def run_comparison(
    file_a: str,
    file_b: str,
    options: ComparisonOptions,
) -> ComparisonResult:
    """Run ncompare on two files and return a structured ComparisonResult.

    - Validates paths and file types via ncompare helpers (read-only).
    - Builds per-file dimensions and variable list using ncompare getters.
    - Calls ncompare.compare() with options; optionally writes text/CSV report.
    - Parses CSV (if written) to fill difference counts and details.
    """
    # ncompare validates paths and types (read-only)
    path_a = ensure_valid_path_exists(file_a)
    path_b = ensure_valid_path_exists(file_b)
    file_a_obj = validate_file_type(path_a)
    file_b_obj = validate_file_type(path_b)

    result = ComparisonResult(
        file_a_path=str(path_a),
        file_b_path=str(path_b),
    )

    # Per-file summaries from ncompare getters (read-only)
    result.dimensions_a = _dimensions_list(file_a_obj)
    result.dimensions_b = _dimensions_list(file_b_obj)
    result.variables_a = _collect_variables_with_shapes(file_a_obj)
    result.variables_b = _collect_variables_with_shapes(file_b_obj)

    # Optional report paths (user can pass from UI for export)
    report_txt = Path(options.report_text_path) if options.report_text_path else None
    report_csv = Path(options.report_csv_path) if options.report_csv_path else None
    if not report_csv:
        # Write CSV to a unique temp file so we can parse summary/diffs
        report_csv = Path(tempfile.gettempdir()) / f"ncompare_{uuid.uuid4().hex[:8]}.csv"

    # Call ncompare.compare() — this is the core ncompare API; we pass options through.
    total = ncompare_compare(
        path_a,
        path_b,
        only_diffs=options.only_differences,
        no_color=True,
        show_chunks=options.include_chunking,
        show_attributes=options.include_attributes,
        file_text=str(report_txt) if report_txt else "",
        file_csv=str(report_csv) if report_csv else "",
        file_xlsx="",
    )
    result.total_differences = total
    if report_csv and report_csv.exists():
        result.report_csv_path = report_csv
        (
            result.variables_only_in_a,
            result.variables_only_in_b,
            result.variables_shared,
            result.groups_only_in_a,
            result.groups_only_in_b,
            result.groups_shared,
            result.attribute_difference_count,
            result.difference_details,
        ) = _parse_csv_for_summary_and_diffs(report_csv)
    if report_txt and Path(report_txt).exists():
        result.report_text_path = report_txt

    return result
