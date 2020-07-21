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

import json
import os
from typing import Dict, List, Union

from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView

from aqt.webview import AnkiWebView
from aqt.qt import qtmajor, qtminor

try:
    from aqt.theme import theme_manager
except (ImportError, ModuleNotFoundError):
    theme_manager = None

parent_dir = os.path.abspath(os.path.dirname(__file__))
package = __name__.split(".")[0]


class GraphWebView(AnkiWebView):
    def __init__(self, mw, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mw = mw
        # prevent UI focus stealing:
        self.setEnabled(False)
        self._load()

    def _load(self):
        base_url = QUrl(
            f"http://localhost:{self._mw.mediaServer.getPort()}/"
            f"_addons/{package}/gui/web/graph.html"
        )

        html_path = os.path.join(parent_dir, "web", "graph.html")
        with open(html_path, "r") as f:
            html = f.read()

        added_classes = []
        if theme_manager and theme_manager.night_mode:
            added_classes.extend(["nightMode", "night_mode"])
        if self._isLegacyQt():
            added_classes.append("legacy_qt")
        
        if added_classes:
            classes_str = " ".join(added_classes)
            html = html.replace("<body>", f"<body class='{classes_str}'>")

        QWebEngineView.setHtml(self, html, baseUrl=base_url)

    def addDataSet(self, label: str, data_set: List[Dict[str, Union[str, int]]]):
        self._runJavascript(
            "newDataSet({})".format(json.dumps(json.dumps([label, data_set])))
        )

    def clearLastDataset(self):
        self._runJavascript("clearLastDataset()")

    def _runJavascript(self, script: str):
        # workaround for widget focus stealing issues
        self.setEnabled(False)
        self.evalWithCallback(script, self.__onJavascriptEvaluated)

    def __onJavascriptEvaluated(self, *args):
        self.setEnabled(True)

    def _isLegacyQt(self):
        return (qtmajor >= 5 and qtminor < 10)
