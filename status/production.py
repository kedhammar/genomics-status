""" Handlers related to data production.
"""
from collections import OrderedDict
from io import BytesIO
from datetime import datetime
import json

from dateutil import parser
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg


from status.util import dthandler, SafeHandler


class ProductionCronjobsHandler(SafeHandler):
    """Returns a JSON document with the Cronjobs database information"""

    def get(self):
        cronjobs = {}
        servers = self.application.cronjobs_db.view("server/alias")
        for server in servers.rows:
            doc = self.application.cronjobs_db.get(server.value)
            cronjobs[server.key] = {
                "last_updated": datetime.strftime(
                    parser.parse(doc["Last updated"]), "%Y-%m-%d %H:%M"
                ),
                "users": doc["users"],
                "server": server.key,
            }
        template = self.application.loader.load("cronjobs.html")
        self.write(
            template.generate(
                gs_globals=self.application.gs_globals,
                cronjobs=cronjobs,
                user=self.get_current_user(),
            )
        )


# Do these following work at all?
class DeliveredMonthlyDataHandler(SafeHandler):
    """Gives the data for monthly delivered amount of basepairs.

    Loaded through /api/v1/delivered_monthly url
    """

    def get(self):
        start_date = self.get_argument("start", "2012-01-01T00:00:00")
        end_date = self.get_argument("end", None)

        self.set_header("Content-type", "application/json")
        self.write(json.dumps(self.delivered(start_date, end_date), default=dthandler))

    def delivered(self, start_date=None, end_date=None):
        if start_date:
            start_date = parser.parse(start_date)

        if end_date:
            end_date = parser.parse(end_date)
        else:
            end_date = datetime.now()

        view = self.application.projects_db.view("date/m_bp_delivered", group_level=3)

        delivered = OrderedDict()

        start = [
            start_date.year,
            (start_date.month - 1) // 3 + 1,
            start_date.month,
            start_date.day,
        ]

        end = [
            end_date.year,
            (end_date.month - 1) // 3 + 1,
            end_date.month,
            end_date.day,
        ]

        for row in view[start:end]:
            y = row.key[0]
            m = row.key[2]
            delivered[dthandler(datetime(y, m, 1))] = int(row.value * 1e6)

        return delivered


class DeliveredMonthlyPlotHandler(DeliveredMonthlyDataHandler):
    """Gives a bar plot for monthly delivered amount of basepairs.

    Loaded through /api/v1/delivered_monthly.png url
    """

    def get(self):
        start_date = self.get_argument("start", "2012-01-01T00:00:00")
        end_date = self.get_argument("end", None)

        delivered = self.delivered(start_date, end_date)

        fig = plt.figure(figsize=[10, 8])
        ax = fig.add_subplot(111)

        dates = [parser.parse(d) for d in delivered.keys()]
        values = list(delivered.values())

        ax.bar(dates, values, width=10)

        ax.set_xticks(dates)
        ax.set_xticklabels([d.strftime("%Y\n%B") for d in dates])

        ax.set_title("Basepairs delivered per month")

        FigureCanvasAgg(fig)

        buf = BytesIO()
        fig.savefig(buf, format="png")
        delivered = buf.getvalue()

        self.set_header("Content-Type", "image/png")
        self.set_header("Content-Length", len(delivered))
        self.write(delivered)


class DeliveredQuarterlyDataHandler(SafeHandler):
    """Gives the data for quarterly delivered amount of basepairs.

    Loaded through /api/v1/delivered_quarterly url
    """

    def get(self):
        start_date = self.get_argument("start", "2012-01-01T00:00:00")
        end_date = self.get_argument("end", None)

        self.set_header("Content-type", "application/json")
        self.write(json.dumps(self.delivered(start_date, end_date), default=dthandler))

    def delivered(self, start_date=None, end_date=None):
        if start_date:
            start_date = parser.parse(start_date)

        if end_date:
            end_date = parser.parse(end_date)
        else:
            end_date = datetime.now()

        view = self.application.projects_db.view("date/m_bp_delivered", group_level=2)

        delivered = OrderedDict()

        start = [
            start_date.year,
            (start_date.month - 1) // 3 + 1,
            start_date.month,
            start_date.day,
        ]

        end = [
            end_date.year,
            (end_date.month - 1) // 3 + 1,
            end_date.month,
            end_date.day,
        ]

        for row in view[start:end]:
            y = row.key[0]
            q = row.key[1]
            delivered[dthandler(datetime(y, (q - 1) * 3 + 1, 1))] = int(row.value * 1e6)

        return delivered


class DeliveredQuarterlyPlotHandler(DeliveredQuarterlyDataHandler):
    """Gives a bar plot for quarterly delivered amount of basepairs.

    Loaded through /api/v1/delivered_quarterly.png
    """

    def get(self):
        start_date = self.get_argument("start", "2012-01-01T00:00:00")
        end_date = self.get_argument("end", None)

        delivered = self.delivered(start_date, end_date)

        fig = plt.figure(figsize=[10, 8])
        ax = fig.add_subplot(111)

        dates = [parser.parse(d) for d in delivered.keys()]
        values = list(delivered.values())

        ax.bar(dates, values)

        ax.set_xticks(dates)
        labels = []
        for d in dates:
            labels.append("{}\nQ{}".format(d.year, (d.month - 1) // 3 + 1))

        ax.set_xticklabels(labels)

        ax.set_title("Basepairs delivered per quarter")

        FigureCanvasAgg(fig)

        buf = BytesIO()
        fig.savefig(buf, format="png")
        delivered = buf.getvalue()

        self.set_header("Content-Type", "image/png")
        self.set_header("Content-Length", len(delivered))
        self.write(delivered)
