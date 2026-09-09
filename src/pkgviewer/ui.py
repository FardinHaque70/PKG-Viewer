from collections import deque
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QImage, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .extract import CollisionPolicy, ExtractionService
from .icon_preview import IconPreview
from .library import discover_packages, game_identity
from .reports import ReportWriter, to_text
from .services import PackageService, classify_package, format_size, region_display

PATH_ROLE = Qt.ItemDataRole.UserRole
NODE_ROLE = Qt.ItemDataRole.UserRole + 1
TYPE_ORDER = ("Base Game", "Update", "DLC", "Other")


class LoadJob(QThread):
    completed = Signal(int, object, str)

    def __init__(self, token, kind, path, generation, service, parent):
        super().__init__(parent)
        self.token, self.kind, self.path = token, kind, path
        self.generation, self.service = generation, service

    def run(self):
        try:
            result = (discover_packages(self.path, self.isInterruptionRequested)
                      if self.kind == "scan" else self.service.inspect(self.path))
            self.completed.emit(self.token, result, "")
        except (OSError, ValueError, RuntimeError) as error:
            self.completed.emit(self.token, None, str(error))


class ExtractJob(QThread):
    progress_changed = Signal(int, int, int, int)
    completed = Signal(object)

    def __init__(self, service, document, entries, destination, policy, parent=None):
        super().__init__(parent)
        self.service, self.document = service, document
        self.entries, self.destination, self.policy = entries, destination, policy

    def run(self):
        summary = self.service.extract_many(
            self.document, self.entries, self.destination, self.policy,
            self.isInterruptionRequested,
            lambda index, total, written, size: self.progress_changed.emit(index, total, written, size))
        self.completed.emit(summary)


class Window(QMainWindow):
    def __init__(self, service=None):
        super().__init__()
        self.service = service or PackageService()
        self.extractor = ExtractionService()
        self.extract_job = None
        self.extract_progress = None
        self.records, self.pending, self.errors, self.jobs = {}, {}, {}, {}
        self._queue = deque()
        self._next_token = 0
        self._generation = 0
        self._closing = False
        self._selected_path = None
        self._nodes = {}
        self._leaves = {}
        self._expanded = {}
        self.setWindowTitle("PS4-pkg-viewer")
        self.resize(1055, 422)
        self.setMinimumSize(700, 360)
        self.setAcceptDrops(True)
        self.build()

    def build(self):
        self.buttons = {}
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(10, 8, 10, 8)
        splitter = QSplitter()
        self.files = QTreeWidget()
        self.files.setHeaderLabel("Games / package types")
        self.files.setAccessibleName("Package library")
        self.files.setRootIsDecorated(True)
        self.files.setItemsExpandable(True)
        self.files.setAlternatingRowColors(True)
        self.files.setUniformRowHeights(True)
        self.files.setIndentation(16)
        self.files.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.files.setMinimumWidth(180)
        self.files.currentItemChanged.connect(self.select_item)
        self.files.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.files.customContextMenuRequested.connect(self.show_library_context_menu)
        splitter.addWidget(self.files)
        self.tabs = QTabWidget()
        overview = QWidget()
        ov = QHBoxLayout(overview)
        frame = QFrame()
        frame.setObjectName("iconFrame")
        fl = QVBoxLayout(frame)
        label = QLabel("icon0")
        label.setAlignment(Qt.AlignCenter)
        fl.addWidget(label)
        self.icon = IconPreview()
        fl.addWidget(self.icon, 1)
        ov.addWidget(frame, 1)
        self.info = self.make_table(["Key", "Information"])
        self.info.setColumnWidth(0, 120)
        ov.addWidget(self.info, 2)
        self.tabs.addTab(overview, "Overview")
        self.validation = QTextEdit()
        self.validation.setReadOnly(True)
        self.tabs.addTab(self.tab_with_actions(
            self.validation, [("Copy report", self.copy_report)]), "Validation")
        self.entries = self.make_table(["ID", "Name", "Offset", "Size", "Encrypted"])
        self.entries.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.tabs.addTab(self.tab_with_actions(self.entries, [
            ("Extract selected", self.extract_selected), ("Extract all", self.extract_all),
        ]), "Entries")
        self.trophies = QTextEdit()
        self.trophies.setReadOnly(True)
        self.tabs.addTab(self.trophies, "Trophies")
        self.advanced = QTextEdit()
        self.advanced.setReadOnly(True)
        self.tabs.addTab(self.advanced, "Advanced")
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 775])
        outer.addWidget(splitter, 1)
        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        bottom.addStretch()
        for text, callback in [
            ("Open PKG", self.open_files), ("Open folder", self.open_folder),
        ]:
            bottom.addWidget(self.make_button(text, callback))
        export_button = QPushButton("Export reports ▾")
        export_button.setMinimumWidth(142)
        self.buttons["Export"] = export_button
        self.export_menu = QMenu(export_button)
        self.export_menu.addAction("Text report…", self.export_text)
        self.export_menu.addAction("JSON report…", self.export_json)
        export_button.setMenu(self.export_menu)
        bottom.addWidget(export_button)
        bottom.addSpacing(8)
        outer.addLayout(bottom)
        self.setCentralWidget(root)
        self.clear_action = self.menuBar().addMenu("Library").addAction("Clear library")
        self.clear_action.triggered.connect(self.clear_items)
        self.remove_action = QAction("Remove from library", self)
        self.remove_action.triggered.connect(self.remove_item)
        self.entries.itemSelectionChanged.connect(self.update_actions)
        self.statusBar().hide()
        self.setStyleSheet("""
            QWidget { background:#303033; color:#ededed; font-size:13px; }
            QFrame#iconFrame { background:#252527; border:1px solid #555; border-radius:6px; }
            QFrame#icon { background:#1e1e20; border:1px solid #49494e; }
            QTreeWidget,QTableWidget,QTextEdit {
                background:#202022; alternate-background-color:#2c2c30;
                gridline-color:#414146; selection-background-color:#57526a;
            }
            QTreeView::item { min-height:24px; }
            QHeaderView::section { background:#29292c; color:white; padding:5px; }
            QPushButton { background:#68636f; color:white; border:1px solid #85808d;
                border-radius:5px; padding:7px 9px; }
            QPushButton:hover:enabled { background:#7b7485; border-color:#a49bae; }
            QPushButton:focus:enabled { border-color:#b8d8ff; }
            QPushButton:pressed:enabled { background:#49424f; padding-top:8px; padding-bottom:6px; }
            QPushButton:disabled { background:#3c3b40; color:#85828b; border-color:#4c4952; }
            QScrollBar:vertical { background:#202022; width:10px; margin:2px 2px 2px 0; border-radius:5px; }
            QScrollBar::handle:vertical { background:#5b5962; min-height:28px; border-radius:5px; }
            QScrollBar::handle:vertical:hover { background:#77727f; }
            QScrollBar::handle:vertical:pressed { background:#93899f; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
            QScrollBar:horizontal { background:#202022; height:10px; margin:0 2px 2px 2px; border-radius:5px; }
            QScrollBar::handle:horizontal { background:#5b5962; min-width:28px; border-radius:5px; }
            QScrollBar::handle:horizontal:hover { background:#77727f; }
            QScrollBar::handle:horizontal:pressed { background:#93899f; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0; }
        """)
        QShortcut(QKeySequence.StandardKey.Open, self, activated=self.open_files)
        self.update_actions()

    def make_button(self, text, callback):
        button = QPushButton(text)
        button.setMinimumWidth(96)
        button.setAccessibleName(text)
        button.clicked.connect(callback)
        self.buttons[text] = button
        return button

    def tab_with_actions(self, content, actions):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(content, 1)
        bar = QHBoxLayout()
        bar.addStretch()
        for text, callback in actions:
            bar.addWidget(self.make_button(text, callback))
        layout.addLayout(bar)
        return page

    def show_library_context_menu(self, position):
        item = self.files.itemAt(position)
        if item is None:
            return
        self.files.setCurrentItem(item)
        self.update_actions()
        menu = QMenu(self.files)
        menu.addAction(self.remove_action)
        menu.exec(self.files.viewport().mapToGlobal(position))

    @staticmethod
    def make_table(headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        shortcut = QShortcut(QKeySequence.StandardKey.Copy, table)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(lambda: QApplication.clipboard().setText("\n".join(
            "\t".join(table.item(row, column).text() if table.item(row, column) else ""
                      for column in sorted({i.column() for i in table.selectedIndexes() if i.row() == row}))
            for row in sorted({i.row() for i in table.selectedIndexes()})
        )))
        return table

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = []
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.is_dir():
                self.load_folder(str(path))
            elif path.suffix.lower() == ".pkg":
                files.append(str(path))
        self.load_paths(files)
        event.acceptProposedAction()

    def open_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select PS4 PKG files", "", "PKG files (*.pkg *.PKG)")
        self.load_paths(paths)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open folder — find all PKGs")
        if folder:
            self.load_folder(folder)

    def load_folder(self, folder):
        folder = str(Path(folder).resolve())
        if self._closing or any(j.kind == "scan" and j.path == folder for j in self.jobs.values()):
            return
        self.statusBar().showMessage(f"Searching {Path(folder).name} and subfolders…")
        self.start_job(self.new_token(), "scan", folder)

    def new_token(self):
        self._next_token += 1
        return self._next_token

    def load_paths(self, paths):
        if self._closing:
            return 0
        added = 0
        for path in paths:
            path = str(Path(path).resolve())
            if path in self.records or path in self.pending:
                continue
            token = self.new_token()
            self.errors.pop(path, None)
            self.pending[path] = token
            self._queue.append((token, path))
            if not self._selected_path and not self.records:
                self._selected_path = path
            added += 1
        self.rebuild_sidebar()
        self.pump_queue()
        return added

    def pump_queue(self):
        if self._closing:
            return
        active = sum(job.kind == "inspect" for job in self.jobs.values())
        while self._queue and active < 2:
            token, path = self._queue.popleft()
            if self.pending.get(path) != token:
                continue
            self.start_job(token, "inspect", path)
            active += 1

    def start_job(self, token, kind, path):
        job = LoadJob(token, kind, path, self._generation, self.service, self)
        self.jobs[token] = job
        job.completed.connect(self.job_completed)
        job.finished.connect(self.job_finished)
        job.start()

    @Slot(int, object, str)
    def job_completed(self, token, result, error):
        job = self.jobs.get(token)
        if not job or self._closing or job.generation != self._generation:
            return
        if job.kind == "scan":
            if error:
                self.statusBar().showMessage(f"Folder scan failed: {error}")
            else:
                added = self.load_paths(result.paths)
                detail = f"Found {len(result.paths)} PKGs; added {added}."
                if result.errors:
                    detail += " Some folders could not be read: " + "; ".join(result.errors)
                self.statusBar().showMessage(detail)
            return
        if self.pending.get(job.path) != token:
            return  # Cleared, removed, or replaced while the worker was running.
        self.pending.pop(job.path)
        if error:
            self.errors[job.path] = error
        else:
            self.records[job.path] = result
        self.rebuild_sidebar()
        self.statusBar().showMessage(
            f"{Path(job.path).name}: {error or result[1].status.value}"
            + (f" — {len(self.pending)} remaining" if self.pending else "")
        )

    @Slot()
    def job_finished(self):
        job = self.sender()
        self.jobs.pop(job.token, None)
        job.deleteLater()
        if self._closing:
            if not self.jobs:
                QTimer.singleShot(0, self.close)
        else:
            self.pump_queue()

    def rebuild_sidebar(self):
        current = self.files.currentItem()
        selected_node = current.data(0, NODE_ROLE) if current else None
        for key, item in self._nodes.items():
            if item.childCount():
                self._expanded[key] = item.isExpanded()
        self.files.blockSignals(True)
        self.files.clear()
        self._nodes, self._leaves = {}, {}
        groups = {}
        for path, record in self.records.items():
            key, title_id = game_identity(record[0])
            groups.setdefault(key, []).append((path, record, title_id))

        def preferred(items):
            return min(items, key=lambda item: (TYPE_ORDER.index(classify_package(item[1][0])), item[0]))

        for key, items in sorted(groups.items(), key=lambda group: (preferred(group[1])[1][2].title.casefold(), group[0])):
            path, record, title_id = preferred(items)
            title = record[2].title or title_id or Path(path).stem
            game = self.add_node(None, key, title + (f" [{title_id}]" if title_id else ""))
            for kind in TYPE_ORDER:
                members = [item for item in items if classify_package(item[1][0]) == kind]
                if not members:
                    continue
                branch = self.add_node(game, key + "/" + kind, f"{kind} ({len(members)})")
                for path, record, _ in sorted(members, key=lambda item: Path(item[0]).name.casefold()):
                    self.add_leaf(branch, path, record[1].status.value)
        for key, title, paths in [("loading", "Loading", self.pending), ("failed", "Unreadable", self.errors)]:
            if paths:
                branch = self.add_node(None, key, f"{title} ({len(paths)})")
                for path in sorted(paths, key=str.casefold):
                    self.add_leaf(branch, path, "Loading" if key == "loading" else "Fail")
        selected = self._leaves.get(self._selected_path) if self._selected_path else self._nodes.get(selected_node)
        if selected:
            self.files.setCurrentItem(selected)
        self.files.blockSignals(False)
        self.select_item(selected, None)

    def add_node(self, parent, key, text):
        item = QTreeWidgetItem([text])
        item.setData(0, NODE_ROLE, key)
        item.setToolTip(0, text)
        if parent:
            parent.addChild(item)
        else:
            self.files.addTopLevelItem(item)
        item.setExpanded(self._expanded.get(key, True))
        self._nodes[key] = item
        return item

    def add_leaf(self, parent, path, status):
        marker = {"Pass": "✓", "Warning": "⚠", "Fail": "✗", "Loading": "…"}.get(status, "○")
        item = QTreeWidgetItem([f"{marker} {Path(path).name}"])
        item.setData(0, PATH_ROLE, path)
        item.setToolTip(0, f"{path}\n{self.errors.get(path, status)}")
        parent.addChild(item)
        self._leaves[path] = item

    def select_item(self, item, old):
        self._selected_path = item.data(0, PATH_ROLE) if item else None
        if self._selected_path in self.records:
            self.show_record(self._selected_path)
        else:
            self.clear_details()
            if self._selected_path in self.errors:
                self.validation.setPlainText(self.errors[self._selected_path])
            elif self._selected_path in self.pending:
                self.icon.set_message("Reading package…")
        self.update_actions()

    def show_record(self, path):
        doc, report, summary = self.records[path]
        rows = [("Status", report.status.value), ("TITLE", summary.title),
                ("CONTENT_ID", summary.content_id), ("TITLE_ID", summary.title_id),
                ("TYPE", classify_package(doc)), ("APP_VER", summary.version),
                ("VERSION", str(doc.metadata.get("VERSION", ""))), ("FIRMWARE", summary.firmware),
                ("REGION", region_display(doc)), ("CATEGORY", summary.category),
                ("SDK_VERSION", summary.sdk_version), ("PUBTOOLINFO", summary.pubtool_info),
                ("Size", format_size(summary.size))]
        self.info.setRowCount(len(rows))
        for i, (key, value) in enumerate(rows):
            self.info.setItem(i, 0, QTableWidgetItem(key))
            self.info.setItem(i, 1, QTableWidgetItem(value))
        self.validation.setPlainText(to_text(report))
        trophy_lines = []
        trophy_doc = doc.trophies
        if not trophy_doc or trophy_doc.availability.value == "Not present":
            trophy_lines = ["No trophy data found."]
        else:
            trophy_lines = [f"Status: {trophy_doc.availability.value}", f"Trophies: {len(trophy_doc.trophies)}", ""]
            for trophy in trophy_doc.trophies:
                if trophy.hidden:
                    trophy_lines.append(f"[{trophy.trophy_type.value}] #{trophy.trophy_id:03d} — Hidden trophy")
                else:
                    trophy_lines.append(f"[{trophy.trophy_type.value}] #{trophy.trophy_id:03d} — {trophy.name or 'Unnamed'}")
                    trophy_lines.append(f"  {trophy.description or 'No description available.'}")
        self.trophies.setPlainText("\n".join(trophy_lines))
        self.entries.setRowCount(len(doc.entries))
        for i, entry in enumerate(doc.entries):
            for j, value in enumerate((f"0x{entry.entry_id:X}", entry.name or "", hex(entry.offset), str(entry.size), str(entry.encrypted))):
                self.entries.setItem(i, j, QTableWidgetItem(value))
        h = doc.header
        advanced = ["PACKAGE", f"  raw type: 0x{summary.package_type_raw:X}",
                    f"  type: {summary.package_type}", f"  DRM: {summary.drm_type}",
                    f"  content type: {summary.content_type}", f"  flags: {summary.content_flags}",
                    f"  file count: {summary.file_count}", f"  entry count: {len(doc.entries)}",
                    "RANGES", f"  table: 0x{h.table_offset:X} ({len(doc.entries) * 0x20} bytes)",
                    f"  body: 0x{h.body_offset:X} ({h.body_size} bytes)",
                    f"  content/PFS: 0x{h.content_offset:X} ({h.content_size} bytes)",
                    "INTEGRITY"]
        for check in report.checks:
            if check.check_id.startswith("pkg.integrity"):
                advanced.append(f"  {check.check_id}: {check.status.value} — {check.message}")
        advanced.append("SFO")
        for key, value in doc.sfo.values.items() if doc.sfo else []:
            advanced.append(f"  {key}: {value.value!r} raw={value.raw.hex()} format=0x{value.format:X}")
        if doc.diagnostics:
            advanced.append("DIAGNOSTICS")
            advanced.extend(f"  [{d.severity.value}] {d.check_id}: {d.message}" for d in doc.diagnostics)
        self.advanced.setPlainText("\n".join(advanced))
        self.load_icon(doc)

    def load_icon(self, doc):
        entry = next((entry for entry in doc.entries if entry.entry_id == 0x1200 and not entry.encrypted), None)
        if not entry or not doc.icon_data:
            self.icon.set_message("icon0 not available")
            return
        try:
            image = QImage.fromData(doc.icon_data)
            if image.isNull():
                raise ValueError("Invalid icon")
            self.icon.set_image(image)
        except (OSError, ValueError):
            self.icon.set_message("icon0 unavailable")

    def current(self):
        item = self.files.currentItem()
        return self.records.get(item.data(0, PATH_ROLE)) if item else None

    def update_actions(self):
        loaded = self.current() is not None
        for name in ("Copy report", "Export"):
            self.buttons[name].setEnabled(loaded)
        for action in self.export_menu.actions():
            action.setEnabled(loaded)
        can_extract = loaded and self.extract_job is None
        self.buttons["Extract selected"].setEnabled(can_extract and bool(self.entries.selectedIndexes()))
        self.buttons["Extract all"].setEnabled(can_extract and self.entries.rowCount() > 0)
        self.remove_action.setEnabled(self.files.currentItem() is not None)
        self.clear_action.setEnabled(bool(self.records or self.pending or self.errors))

    def copy_report(self):
        record = self.current()
        if record:
            QApplication.clipboard().setText(to_text(record[1]))
            self.statusBar().showMessage("Report copied to clipboard")

    def export_text(self):
        self.export_current(False)

    def export_json(self):
        self.export_current(True)

    def _extract(self, entries):
        record = self.current()
        if not record or not entries or self.extract_job:
            return
        folder = QFileDialog.getExistingDirectory(self, "Choose extraction folder")
        if not folder:
            return
        choice = QMessageBox(self)
        choice.setWindowTitle("Extraction collision policy")
        choice.setText("How should existing destination files be handled?")
        skip = choice.addButton("Skip", QMessageBox.ButtonRole.AcceptRole)
        keep = choice.addButton("Keep both", QMessageBox.ButtonRole.ActionRole)
        overwrite = choice.addButton("Overwrite", QMessageBox.ButtonRole.DestructiveRole)
        choice.setDefaultButton(skip)
        choice.exec()
        policy = {skip: CollisionPolicy.SKIP, keep: CollisionPolicy.KEEP_BOTH,
                  overwrite: CollisionPolicy.OVERWRITE}.get(choice.clickedButton())
        if policy is None:
            return
        self.extract_progress = QProgressDialog("Preparing extraction…", "Cancel", 0, 100, self)
        self.extract_progress.setWindowTitle("Extracting PKG entries")
        self.extract_progress.setAutoClose(False)
        self.extract_progress.canceled.connect(self.cancel_extraction)
        self.extract_progress.show()
        self.extract_job = ExtractJob(self.extractor, record[0], entries, folder, policy, self)
        self.extract_job.progress_changed.connect(self.extraction_progress)
        self.extract_job.completed.connect(self.extraction_completed)
        self.extract_job.finished.connect(self.extraction_finished)
        self.extract_job.start()
        self.update_actions()

    @Slot()
    def cancel_extraction(self):
        if self.extract_job:
            self.extract_job.requestInterruption()
            self.statusBar().showMessage("Cancelling extraction…")

    @Slot(int, int, int, int)
    def extraction_progress(self, index, total, written, size):
        if self.extract_progress:
            self.extract_progress.setValue(int(index * 100 / max(total, 1)))
            self.extract_progress.setLabelText(f"Extracting entry {index} of {total} — {written:,} / {size:,} bytes")

    @Slot(object)
    def extraction_completed(self, summary):
        failed = sum(result.status == "Failed" for result in summary.results)
        message = f"Extracted {summary.completed} entries"
        if failed:
            message += f"; {failed} failed"
        if summary.cancelled:
            message += "; cancelled"
        self.statusBar().showMessage(message)

    @Slot()
    def extraction_finished(self):
        if self.extract_progress:
            self.extract_progress.close()
            self.extract_progress.deleteLater()
            self.extract_progress = None
        self.extract_job.deleteLater()
        self.extract_job = None
        self.update_actions()

    def extract_selected(self):
        record = self.current()
        if not record:
            return
        rows = {index.row() for index in self.entries.selectedIndexes()}
        self._extract([record[0].entries[row] for row in sorted(rows)])

    def extract_all(self):
        record = self.current()
        if record:
            self._extract(record[0].entries)

    def export_current(self, json):
        record = self.current()
        if not record:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export report", "validation.json" if json else "validation.txt")
        if path:
            try:
                (ReportWriter.write_json if json else ReportWriter.write_text)(record[1], path)
                self.statusBar().showMessage(f"Report saved to {path}")
            except OSError as error:
                self.statusBar().showMessage(f"Export failed: {error}")

    def remove_item(self):
        item = self.files.currentItem()
        if not item:
            return
        stack = [item]
        removed = 0
        while stack:
            node = stack.pop()
            stack.extend(node.child(i) for i in range(node.childCount()))
            path = node.data(0, PATH_ROLE)
            if path:
                self.records.pop(path, None)
                self.pending.pop(path, None)
                self.errors.pop(path, None)
                removed += 1
        self._selected_path = None
        self.rebuild_sidebar()
        self.statusBar().showMessage(f"Removed {removed} packages from the list")

    def clear_details(self):
        self.info.setRowCount(0)
        self.validation.clear()
        self.entries.setRowCount(0)
        self.advanced.clear()
        self.trophies.clear()
        self.icon.set_message("Drop a PKG file here")

    def clear_items(self):
        self._generation += 1
        self.records.clear()
        self.pending.clear()
        self.errors.clear()
        self._queue.clear()
        self._selected_path = None
        for job in self.jobs.values():
            job.requestInterruption()
        self.rebuild_sidebar()
        self.statusBar().showMessage("Package list cleared")

    def closeEvent(self, event):
        self._closing = True
        self._queue.clear()
        for job in self.jobs.values():
            job.requestInterruption()
        if self.jobs:
            self.statusBar().showMessage("Finishing active reads before closing…")
            event.ignore()
        else:
            event.accept()


def build_window(service=None):
    return Window(service)
