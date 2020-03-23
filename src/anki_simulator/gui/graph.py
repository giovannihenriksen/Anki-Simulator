import json
import os
from datetime import date

from aqt.webview import AnkiWebView

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
        html = "<head><meta charset=\"UTF-8\"><script>{}</script>".format(open(pathChart, 'r').read())
        html += open(path, 'r').read()
        self.setHtml(html)

    def addDataSet(self, label, set):
        self.eval("newDataSet('{}', '{}')".format(label, json.dumps(set, default=json_serial)))

    def clearLastDataset(self):
        self.eval("clearLastDataset()")
