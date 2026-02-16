"""Main application window for netCDF-viewer."""

import logging

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QCheckBox,
    QMessageBox,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QTabWidget,
    QTextEdit,
)
from PySide6.QtCore import QThread, Signal, QObject

from netcdf_viewer.models.comparison_result import ComparisonOptions, ComparisonResult
from netcdf_viewer.services.compare_service import run_comparison


class CompareWorker(QObject):
    """Worker that runs comparison in a background thread."""

    finished = Signal(object)  # ComparisonResult or None
    error = Signal(str)

    def __init__(self, file_a: str, file_b: str, options: ComparisonOptions) -> None:
        super().__init__()
        self._file_a = file_a
        self._file_b = file_b
        self._options = options

    def run(self) -> None:
        logger = logging.getLogger("netcdf_viewer.gui")
        try:
            result = run_comparison(self._file_a, self._file_b, self._options)
            self.finished.emit(result)
        except Exception as e:  # noqa: BLE001
            logger.exception("Comparison failed: %s", e)
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Main window: file selectors, options, Compare button, results."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("netCDF-viewer")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # --- File selection ---
        file_group = QGroupBox("Files to compare")
        file_layout = QVBoxLayout(file_group)

        for label, attr in [("File A", "file_a_edit"), ("File B", "file_b_edit")]:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{label}:"))
            edit = QLineEdit()
            edit.setPlaceholderText("Select a netCDF or HDF5 file...")
            edit.setReadOnly(True)
            setattr(self, attr, edit)
            row.addWidget(edit)
            btn = QPushButton("Browse…")
            setattr(self, f"{attr.replace('_edit', '_btn')}", btn)
            btn.clicked.connect(lambda checked=False, e=edit: self._browse(e))
            row.addWidget(btn)
            file_layout.addLayout(row)

        layout.addWidget(file_group)

        # --- Options (all ncompare options visible) ---
        options_group = QGroupBox("Comparison options")
        options_layout = QVBoxLayout(options_group)
        self.only_differences_cb = QCheckBox("Show only differences")
        self.only_differences_cb.setToolTip("Only show variables/attributes that differ (ncompare: only_diffs)")
        self.include_attributes_cb = QCheckBox("Include attributes")
        self.include_attributes_cb.setChecked(True)
        self.include_attributes_cb.setToolTip("Include variable attributes in comparison (ncompare: show_attributes)")
        self.include_chunking_cb = QCheckBox("Include chunking details")
        self.include_chunking_cb.setToolTip("Include chunk sizes in variable comparison (ncompare: show_chunks)")
        options_layout.addWidget(self.only_differences_cb)
        options_layout.addWidget(self.include_attributes_cb)
        options_layout.addWidget(self.include_chunking_cb)
        layout.addWidget(options_group)

        # --- Compare button and progress ---
        btn_layout = QHBoxLayout()
        self.compare_btn = QPushButton("Compare")
        self.compare_btn.setDefault(True)
        self.compare_btn.clicked.connect(self._on_compare)
        btn_layout.addWidget(self.compare_btn)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.setVisible(False)
        btn_layout.addWidget(self.progress_bar)
        layout.addLayout(btn_layout)

        # --- Results area ---
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)

        self.results_tabs = QTabWidget()
        # Summary tab: per-file dimensions and variable table
        summary_widget = QWidget()
        summary_layout = QVBoxLayout(summary_widget)
        self.summary_file_a_label = QLabel("File A: (no comparison yet)")
        self.summary_file_a_label.setWordWrap(True)
        self.summary_file_b_label = QLabel("File B: (no comparison yet)")
        self.summary_file_b_label.setWordWrap(True)
        summary_layout.addWidget(self.summary_file_a_label)
        summary_layout.addWidget(self.summary_file_b_label)
        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(4)
        self.summary_table.setHorizontalHeaderLabels(["Source", "Variable", "Shape", "Point count"])
        self.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        summary_layout.addWidget(self.summary_table)
        self.results_tabs.addTab(summary_widget, "Summary")

        # Differences tab
        diff_widget = QWidget()
        diff_layout = QVBoxLayout(diff_widget)
        self.diff_text = QTextEdit()
        self.diff_text.setReadOnly(True)
        self.diff_text.setPlaceholderText("Run a comparison to see non-matching groups, variables, and attribute differences.")
        diff_layout.addWidget(self.diff_text)
        self.results_tabs.addTab(diff_widget, "Differences")

        results_layout.addWidget(self.results_tabs)
        layout.addWidget(results_group)

        self._worker: CompareWorker | None = None
        self._thread: QThread | None = None

    def _browse(self, line_edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select netCDF or HDF5 file",
            "",
            "netCDF/HDF5 (*.nc *.nc3 *.nc4 *.h5 *.hdf5 *.he5);;All files (*)",
        )
        if path:
            line_edit.setText(path)

    def _on_compare(self) -> None:
        file_a = self.file_a_edit.text().strip()
        file_b = self.file_b_edit.text().strip()
        if not file_a or not file_b:
            QMessageBox.warning(
                self,
                "Missing files",
                "Please select both File A and File B before comparing.",
            )
            return

        options = ComparisonOptions(
            only_differences=self.only_differences_cb.isChecked(),
            include_attributes=self.include_attributes_cb.isChecked(),
            include_chunking=self.include_chunking_cb.isChecked(),
        )

        self.compare_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self._clear_results()

        self._thread = QThread()
        self._worker = CompareWorker(file_a, file_b, options)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_compare_finished)
        self._worker.error.connect(self._on_compare_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _clear_results(self) -> None:
        self.summary_file_a_label.setText("File A: (running comparison…)")
        self.summary_file_b_label.setText("File B: (running comparison…)")
        self.summary_table.setRowCount(0)
        self.diff_text.clear()

    def _on_compare_finished(self, result: ComparisonResult | None) -> None:
        self.compare_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        if result is None:
            return
        self._display_result(result)

    def _on_compare_error(self, message: str) -> None:
        self.compare_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(
            self,
            "Comparison error",
            f"An error occurred while comparing the files:\n\n{message}",
        )
        self._clear_results()

    def _display_result(self, result: ComparisonResult) -> None:
        def dims_str(dims: list) -> str:
            if not dims:
                return "—"
            return ", ".join(f"{n}={s}" for n, s in dims)
        self.summary_file_a_label.setText(f"File A: {result.file_a_path} — dimensions: {dims_str(result.dimensions_a)}; variables: {len(result.variables_a)}")
        self.summary_file_b_label.setText(f"File B: {result.file_b_path} — dimensions: {dims_str(result.dimensions_b)}; variables: {len(result.variables_b)}")

        # Variable table: merge variables from both files with source column
        rows: list[tuple[str, str, str, str]] = []
        for name, shape, count in result.variables_a:
            rows.append(("File A", name, shape, str(count)))
        for name, shape, count in result.variables_b:
            rows.append(("File B", name, shape, str(count)))
        self.summary_table.setRowCount(len(rows))
        for i, (src, name, shape, count) in enumerate(rows):
            self.summary_table.setItem(i, 0, QTableWidgetItem(src))
            self.summary_table.setItem(i, 1, QTableWidgetItem(name))
            self.summary_table.setItem(i, 2, QTableWidgetItem(shape))
            self.summary_table.setItem(i, 3, QTableWidgetItem(count))

        # Differences panel
        lines = [
            f"Total differences: {result.total_differences}",
            f"Variables — only in A: {result.variables_only_in_a}, only in B: {result.variables_only_in_b}, shared: {result.variables_shared}",
            f"Groups — only in A: {result.groups_only_in_a}, only in B: {result.groups_only_in_b}, shared: {result.groups_shared}",
            f"Attribute differences: {result.attribute_difference_count}",
            "",
        ]
        if result.difference_details:
            lines.append("--- Detail ---")
            for info, val_a, val_b in result.difference_details[:200]:  # limit for display
                lines.append(f"  {info}: A={val_a!r} | B={val_b!r}")
            if len(result.difference_details) > 200:
                lines.append(f"  ... and {len(result.difference_details) - 200} more.")
        if result.report_csv_path:
            lines.append(f"\nReport (CSV): {result.report_csv_path}")
        if result.report_text_path:
            lines.append(f"Report (text): {result.report_text_path}")
        self.diff_text.setPlainText("\n".join(lines))

    def closeEvent(self, event) -> None:
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)
        event.accept()
