from __future__ import annotations

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .storage import SpotRepository
from .theme import TOKENS, semantic_style


TEXT = {
    "CZE": {
        "title": "Přílohy kampaně — {name}",
        "intro": (
            "Soubor se zkopíruje do spravovaného úložiště kampaně. Původní "
            "soubor lze potom přesunout; integritu kopie hlídá SHA-256."
        ),
        "notes": "Krátký popis přílohy",
        "import": "Přidat soubor…",
        "open": "Otevřít vybraný",
        "verify": "Znovu ověřit",
        "close": "Zavřít",
        "headers": [
            "Přidáno UTC",
            "Soubor",
            "Popis",
            "Typ",
            "Velikost",
            "SHA-256",
            "Stav",
        ],
        "status": {
            "ok": "ověřeno",
            "missing": "soubor chybí",
            "size_mismatch": "nesouhlasí velikost",
            "hash_mismatch": "nesouhlasí obsah",
            "unsafe_path": "nebezpečná cesta",
        },
        "error": "Přílohu nelze přidat",
        "open_error": "Soubor se nepodařilo otevřít.",
        "filter": "Podklady měření (*);;Všechny soubory (*)",
    },
    "ENG": {
        "title": "Campaign attachments — {name}",
        "intro": (
            "The file is copied into managed campaign storage. The original may "
            "then be moved; SHA-256 protects the integrity of the managed copy."
        ),
        "notes": "Short attachment description",
        "import": "Add file…",
        "open": "Open selected",
        "verify": "Verify again",
        "close": "Close",
        "headers": [
            "Added UTC",
            "File",
            "Description",
            "Type",
            "Size",
            "SHA-256",
            "Status",
        ],
        "status": {
            "ok": "verified",
            "missing": "file missing",
            "size_mismatch": "size mismatch",
            "hash_mismatch": "content mismatch",
            "unsafe_path": "unsafe path",
        },
        "error": "Cannot add attachment",
        "open_error": "The file could not be opened.",
        "filter": "Measurement evidence (*);;All files (*)",
    },
}


class CampaignAttachmentsDialog(QDialog):
    def __init__(
        self,
        repository: SpotRepository,
        campaign_id: int,
        language: str,
        parent=None,
    ):
        super().__init__(parent)
        self.repository = repository
        self.campaign_id = campaign_id
        self.text = TEXT[language if language in TEXT else "CZE"]
        campaign = repository.get_campaign(campaign_id)
        self.setWindowTitle(self.text["title"].format(name=campaign.name))
        self.resize(1050, 580)

        layout = QVBoxLayout(self)
        intro = QLabel(self.text["intro"])
        intro.setWordWrap(True)
        intro.setStyleSheet(semantic_style("text_secondary"))
        layout.addWidget(intro)

        action_row = QHBoxLayout()
        self.notes = QLineEdit()
        self.notes.setPlaceholderText(self.text["notes"])
        self.import_button = QPushButton(self.text["import"])
        self.open_button = QPushButton(self.text["open"])
        self.open_button.setEnabled(False)
        self.verify_button = QPushButton(self.text["verify"])
        action_row.addWidget(self.notes, 1)
        action_row.addWidget(self.import_button)
        action_row.addWidget(self.open_button)
        action_row.addWidget(self.verify_button)
        layout.addLayout(action_row)

        self.table = QTableWidget(0, len(self.text["headers"]))
        self.table.setHorizontalHeaderLabels(self.text["headers"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        close_button = QPushButton(self.text["close"])
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
        self.import_button.clicked.connect(self.import_file)
        self.open_button.clicked.connect(self.open_selected)
        self.verify_button.clicked.connect(self.refresh)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.table.itemDoubleClicked.connect(lambda *_args: self.open_selected())
        close_button.clicked.connect(self.accept)
        self.refresh()

    def import_file(self) -> None:
        filename, _selected_filter = QFileDialog.getOpenFileName(
            self,
            self.text["import"],
            "",
            self.text["filter"],
        )
        if not filename:
            return
        try:
            self.repository.import_campaign_attachment(
                self.campaign_id,
                filename,
                self.notes.text(),
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, self.text["error"], str(exc))
            return
        self.notes.clear()
        self.refresh()

    def _selected_attachment(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 0)
        attachment_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        if attachment_id is None:
            return None
        return self.repository.get_campaign_attachment(int(attachment_id))

    def _selection_changed(self) -> None:
        self.open_button.setEnabled(self._selected_attachment() is not None)

    def open_selected(self) -> None:
        attachment = self._selected_attachment()
        if attachment is None:
            return
        path = self.repository.campaign_attachment_path(attachment)
        if (
            self.repository.verify_campaign_attachment(attachment) != "ok"
            or not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        ):
            QMessageBox.warning(self, self.text["title"], self.text["open_error"])

    def refresh(self) -> None:
        attachments = self.repository.list_campaign_attachments(self.campaign_id)
        self.table.setRowCount(len(attachments))
        for row, attachment in enumerate(attachments):
            status = self.repository.verify_campaign_attachment(attachment)
            values = (
                attachment.added_at.strftime("%Y-%m-%d %H:%M:%S"),
                attachment.original_name,
                attachment.notes,
                attachment.media_type,
                _format_size(attachment.size_bytes),
                attachment.sha256[:16] + "…",
                self.text["status"][status],
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, attachment.id)
                if column == 6:
                    item.setForeground(
                        QColor(
                            TOKENS.success
                            if status == "ok"
                            else TOKENS.danger_strong
                        )
                    )
                self.table.setItem(row, column, item)
        self.table.resizeColumnsToContents()
        self.open_button.setEnabled(False)


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} kB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"
