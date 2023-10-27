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

from typing import TYPE_CHECKING, cast

from aqt import mw
from aqt.gui_hooks import deck_browser_will_show_options_menu
from aqt.qt import QAction, QMenu

from ._version import __version__  # noqa: F401
from .collection_simulator import CollectionSimulator
from .gui.dialogs import SimulatorDialog
from .review_simulator import ReviewSimulator

if TYPE_CHECKING:
    assert mw is not None
    from aqt.main import AnkiQt


def open_simulator_dialog(main_window: "AnkiQt", deck_id=None):
    dialog = SimulatorDialog(
        main_window, ReviewSimulator, CollectionSimulator, deck_id=deck_id
    )
    dialog.show()


def add_deck_menu_action_factory(main_window: "AnkiQt"):
    def add_deck_menu_action(menu: QMenu, deck_id: int):
        action = cast(QAction, menu.addAction("Simulate"))
        action.triggered.connect(lambda _: open_simulator_dialog(main_window, deck_id))

    return add_deck_menu_action


# Web exports

mw.addonManager.setWebExports(__name__, r"gui(/|\\)web(/|\\).*")

# Main menu

action = QAction("Anki Simulator", mw)
action.triggered.connect(lambda _, mw=mw: open_simulator_dialog(mw))
mw.form.menuTools.addAction(action)

# Deck options context menu

add_deck_menu = add_deck_menu_action_factory(mw)
deck_browser_will_show_options_menu.append(add_deck_menu)
