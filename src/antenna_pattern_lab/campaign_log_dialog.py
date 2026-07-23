from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from .campaigns import CampaignLogEntry, LOG_CATEGORIES
from .storage import SpotRepository
from .theme import semantic_style


TEXT = {
    "CZE": {
        "title": "Deník kampaně — {name}",
        "intro": (
            "Zaznamenejte změny sestavy a podmínky v okamžiku, kdy nastaly. "
            "Položky jsou součástí historie kampaně."
        ),
        "categories": {
            "setup": "Sestava",
            "environment": "Prostředí",
            "antenna_change": "Změna antény",
            "power": "Výkon / napájení",
            "observation": "Pozorování",
            "issue": "Problém",
        },
        "placeholder": "Např. déšť začal v 18:40 UTC; výkon stále 20 W…",
        "add": "Přidat záznam",
        "close": "Zavřít",
        "headers": ["Čas UTC", "Kategorie", "Záznam"],
        "required": "Nejprve napište text záznamu.",
    },
    "ENG": {
        "title": "Campaign log — {name}",
        "intro": (
            "Record setup changes and conditions when they occur. Entries remain "
            "part of the campaign history."
        ),
        "categories": {
            "setup": "Setup",
            "environment": "Environment",
            "antenna_change": "Antenna change",
            "power": "Power / supply",
            "observation": "Observation",
            "issue": "Issue",
        },
        "placeholder": "For example: rain started at 18:40 UTC; power remains 20 W…",
        "add": "Add entry",
        "close": "Close",
        "headers": ["UTC time", "Category", "Entry"],
        "required": "Write the entry text first.",
    },
}


class CampaignLogDialog(QDialog):
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
        self.resize(900, 560)

        layout = QVBoxLayout(self)
        intro = QLabel(self.text["intro"])
        intro.setWordWrap(True)
        intro.setStyleSheet(semantic_style("text_secondary"))
        layout.addWidget(intro)

        entry_row = QHBoxLayout()
        self.category = QComboBox()
        for category in LOG_CATEGORIES:
            self.category.addItem(self.text["categories"][category], category)
        self.entry_text = QTextEdit()
        self.entry_text.setPlaceholderText(self.text["placeholder"])
        self.entry_text.setMaximumHeight(72)
        self.add_button = QPushButton(self.text["add"])
        entry_row.addWidget(self.category)
        entry_row.addWidget(self.entry_text, 1)
        entry_row.addWidget(self.add_button)
        layout.addLayout(entry_row)

        self.message = QLabel()
        self.message.setStyleSheet(semantic_style("danger"))
        layout.addWidget(self.message)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(self.text["headers"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        close_button = QPushButton(self.text["close"])
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
        self.add_button.clicked.connect(self.add_entry)
        close_button.clicked.connect(self.accept)
        self.refresh()

    def add_entry(self) -> None:
        if not self.entry_text.toPlainText().strip():
            self.message.setText(self.text["required"])
            return
        self.repository.add_campaign_log_entry(
            CampaignLogEntry(
                id=None,
                campaign_id=self.campaign_id,
                recorded_at=datetime.now(timezone.utc),
                category=self.category.currentData(),
                text=self.entry_text.toPlainText(),
            )
        )
        self.entry_text.clear()
        self.message.clear()
        self.refresh()

    def refresh(self) -> None:
        entries = self.repository.list_campaign_log_entries(self.campaign_id)
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            values = (
                entry.recorded_at.astimezone(timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                self.text["categories"].get(entry.category, entry.category),
                entry.text,
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
