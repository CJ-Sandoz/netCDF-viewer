"""Structures for comparison options and comparison results.

ComparisonOptions maps to ncompare.compare() parameters so that all options
passed to ncompare are visible in the UI (visibility over automation).
ComparisonResult holds per-file summaries and difference counts produced by
ncompare (and optional report paths).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class ComparisonOptions:
    """Options passed to ncompare; all must be exposed in the GUI."""

    only_differences: bool = False
    """Show only variables/attributes that differ (ncompare: only_diffs)."""

    include_attributes: bool = True
    """Include variable attributes in comparison (ncompare: show_attributes)."""

    include_chunking: bool = False
    """Include chunk sizes in variable comparison (ncompare: show_chunks)."""

    report_text_path: str | Path = ""
    """Optional path to write text report (ncompare: file_text)."""

    report_csv_path: str | Path = ""
    """Optional path to write CSV report (ncompare: file_csv)."""


@dataclass
class ComparisonResult:
    """Result of comparing two netCDF/HDF5 files via ncompare.

    Per-file summary: dimensions and variables (name, shape, point count).
    Difference counts: variables/groups only in A, only in B, shared; attribute diffs.
    Optional paths to text/CSV reports produced by ncompare.
    """

    file_a_path: str = ""
    file_b_path: str = ""

    # Per-file structure (from ncompare getters / file inspection)
    dimensions_a: list[tuple[str, int]] = field(default_factory=list)
    dimensions_b: list[tuple[str, int]] = field(default_factory=list)
    variables_a: list[tuple[str, str, int]] = field(default_factory=list)
    """List of (name, shape_str, point_count) for File A."""
    variables_b: list[tuple[str, str, int]] = field(default_factory=list)
    """List of (name, shape_str, point_count) for File B."""

    # Counts from ncompare (total and breakdown)
    total_differences: int = 0
    variables_only_in_a: int = 0
    variables_only_in_b: int = 0
    variables_shared: int = 0
    groups_only_in_a: int = 0
    groups_only_in_b: int = 0
    groups_shared: int = 0
    attribute_difference_count: int = 0

    # Parsed difference rows (info, value_a, value_b) from ncompare report for display
    difference_details: list[tuple[str, str, str]] = field(default_factory=list)

    # Paths to report files if user requested export
    report_text_path: str | Path = ""
    report_csv_path: str | Path = ""
