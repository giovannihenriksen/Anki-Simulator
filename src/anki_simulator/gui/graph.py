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
from datetime import date

from aqt.webview import AnkiWebView

try:
    from aqt.theme import theme_manager
except (ImportError, ModuleNotFoundError):
    theme_manager = None

parent_dir = os.path.abspath(os.path.dirname(__file__))


class Graph(AnkiWebView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setEnabled(False)
        self.__controls()

    def __controls(self):
        path = os.path.join(parent_dir, "graph.html")
        pathChart = os.path.join(parent_dir, "chart/dist/Chart.bundle.min.js")
        html = '<head><meta charset="UTF-8"><script>{}</script>'.format(
            open(pathChart, "r").read()
        )

        if theme_manager and theme_manager.night_mode:
            html += "<style>#chart{background-color:black;}</style>"
            html += (
                "<script>"
                "Chart.defaults.global.defaultFontColor = 'white';"
                "Chart.defaults.scale.gridLines.color = 'rgba(255, 255, 255, 0.2)';"
                "Chart.defaults.scale.gridLines.zeroLineColor = 'rgba(255, 255, 255, 0.25)';"
                "Chart.defaults.global.tooltips.backgroundColor = 'rgba(255, 255, 255, 0.9)';"
                "Chart.defaults.global.tooltips.bodyFontColor = 'rgba(0, 0, 0, 1)';"
                "Chart.defaults.global.tooltips.titleFontColor = 'rgba(0, 0, 0, 1)';"
                "Chart.defaults.global.tooltips.footerFontColor = 'rgba(0, 0, 0, 1)';"
                "</script>"
            )
        html += open(path, "r").read()
        self.setHtml(html)

    def addDataSet(self, label, data_set):
        self._runJavascript(
            "newDataSet('{}', '{}')".format(label, json.dumps(data_set))
        )

    def clearLastDataset(self):
        self._runJavascript("clearLastDataset()")

    def _runJavascript(self, script: str):
        # workaround for widget focus stealing issues
        self.setEnabled(False)
        self.evalWithCallback(script, self.__onJavascriptEvaluated)

    def __onJavascriptEvaluated(self, *args):
        self.setEnabled(True)
