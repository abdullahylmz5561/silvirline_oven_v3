"""
ui/views/recipes_view.py
===========================
Sol menüden ulaşılan tarif kütüphanesi. Bir tarife dokunmak, fırının
modunu / hedef sıcaklığını / zamanlayıcısını otomatik ayarlar
(controller.apply_recipe) ve ana ekrana döner.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal

from ui.icons import OvenFunctionIcon
from core.recipes_data import RECIPES, CATEGORIES


class RecipeCard(QFrame):
    def __init__(self, recipe, on_click, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setCursor(Qt.PointingHandCursor)
        self.recipe = recipe
        self._on_click = on_click

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        layout.addWidget(OvenFunctionIcon(recipe["mode"], size=30), alignment=Qt.AlignLeft)

        name = QLabel(recipe["name"])
        name.setProperty("class", "funcName")
        layout.addWidget(name)

        meta = QLabel(f'{recipe["temp"]}°C · {recipe["min"]} dk')
        meta.setProperty("class", "dim")
        meta.setStyleSheet("font-family:'JetBrains Mono'; font-size:11px; color:#a89f93;")
        layout.addWidget(meta)

    def mousePressEvent(self, _event):
        self._on_click(self.recipe)


class RecipesView(QWidget):
    recipe_applied = pyqtSignal()

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.active_cat = "Tümü"

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        title = QLabel("Tarifler")
        title.setProperty("class", "title")
        root.addWidget(title)

        cat_row = QHBoxLayout()
        cat_row.setSpacing(8)
        self.cat_buttons = []
        for cat in CATEGORIES:
            btn = QPushButton(cat)
            btn.setProperty("class", "chip")
            btn.setCheckable(True)
            btn.setChecked(cat == "Tümü")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, c=cat: self._filter(c))
            cat_row.addWidget(btn)
            self.cat_buttons.append(btn)
        cat_row.addStretch(1)
        root.addLayout(cat_row)

        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.grid_widget)
        root.addWidget(scroll, stretch=1)

        self._render_grid()

    def _filter(self, cat):
        self.active_cat = cat
        for btn in self.cat_buttons:
            btn.setChecked(btn.text() == cat)
        self._render_grid()

    def _render_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        recipes = RECIPES if self.active_cat == "Tümü" else [
            r for r in RECIPES if r["cat"] == self.active_cat
        ]
        cols = 4
        for i, r in enumerate(recipes):
            card = RecipeCard(r, self._apply_recipe)
            self.grid.addWidget(card, i // cols, i % cols)

    def _apply_recipe(self, recipe):
        self.controller.apply_recipe(recipe["mode"], recipe["temp"], recipe["min"])
        self.recipe_applied.emit()
