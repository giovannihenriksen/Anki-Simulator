import json
import os
from PyQt5.QtWebEngineWidgets import QWebEngineView
from datetime import date

parent_dir = os.path.abspath(os.path.dirname(__file__))


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


class Graph(QWebEngineView):

    def __init__(self):
        super(QWebEngineView, self).__init__()
        self.__controls()

    def __controls(self):
        path = os.path.join(parent_dir, "graph.html")
        pathChart = os.path.join(parent_dir, "chart/dist/Chart.bundle.min.js")
        html = "<head><meta charset=\"UTF-8\"><script>{}</script>".format(open(pathChart, 'r').read())
        html += open(path, 'r').read()
        self.setHtml(html)

    def addDataSet(self, label, set):
        self.page().runJavaScript("newDataSet('{}', '{}')".format(label, json.dumps(set, default=json_serial)))

    def clearLastDataset(self):
        self.page().runJavaScript("clearLastDataset()")
