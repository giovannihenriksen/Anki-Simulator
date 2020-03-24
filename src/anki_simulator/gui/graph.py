import json
import os
from datetime import date

from aqt.webview import AnkiWebView

try:
    from aqt.theme import theme_manager
except (ImportError, ModuleNotFoundError):
    theme_manager = None

parent_dir = os.path.abspath(os.path.dirname(__file__))


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


class Graph(AnkiWebView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

    def addDataSet(self, label, set):
        self.eval(
            "newDataSet('{}', '{}')".format(label, json.dumps(set, default=json_serial))
        )

    def clearLastDataset(self):
        self.eval("clearLastDataset()")
