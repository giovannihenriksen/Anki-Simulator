# Anki Simulator Add-on for Anki
#
# Copyright (C) 2020  GiovanniHenriksen https://github.com/giovannihenriksen
# Copyright (C) 2020  Aristotelis P. https://glutanimate.com/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see https://www.gnu.org/licenses/.

from ._version import __version__  # noqa: F401

# Allows us to use type annotations even on earlier Anki 2.1 releases
# that do not package types and typing
try:
    import typing  # noqa: F401
    import types  # noqa: F401

    # Python 3.8+ test:
    from typing import Literal, Final  # noqa: F401
except ImportError:
    import sys
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "_vendor"))

from PyQt5.QtWidgets import QAction

# import the main window object (mw) from aqt
import aqt

from .collection_simulator import CollectionSimulator
from .gui.dialogs import SimulatorDialog
from .review_simulator import ReviewSimulator


def open_simulator_dialog(deck_id=None):
    dialog = SimulatorDialog(
        aqt.mw, ReviewSimulator, CollectionSimulator, deck_id=deck_id
    )
    dialog.show()


def on_deck_browser_will_show_options_menu(menu, deck_id):
    action = menu.addAction("Simulate")
    action.triggered.connect(lambda _, did=deck_id: open_simulator_dialog(did))


# Web exports

aqt.mw.addonManager.setWebExports(__name__, r"gui(/|\\)web(/|\\).*")

# Main menu

action = QAction("Anki Simulator", aqt.mw)
action.triggered.connect(open_simulator_dialog)  # type: ignore
aqt.mw.form.menuTools.addAction(action)  # type: ignore

# Deck options context menu

try:  # Anki 2.1.20+
    from aqt.gui_hooks import deck_browser_will_show_options_menu

    deck_browser_will_show_options_menu.append(on_deck_browser_will_show_options_menu)
except (ImportError, ModuleNotFoundError):
    from anki.hooks import addHook

    addHook("showDeckOptions", on_deck_browser_will_show_options_menu)
