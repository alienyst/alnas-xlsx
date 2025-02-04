import json

from odoo.http import content_disposition, request, route, serialize_exception
from odoo.tools import html_escape
from odoo.tools.safe_eval import safe_eval

from odoo.addons.web.controllers import main as report


class ReportController(report.ReportController):
    @route()
    def report_routes(self, reportname, docids=None, converter=None, **data):
        if converter == "xlsx_jinja":
            return self._report_routes_xlsx_jinja(reportname, docids, converter, **data)
        return super(ReportController, self).report_routes(
            reportname, docids, converter, **data
        )

    def _report_routes_xlsx_jinja(self, reportname, docids=None, converter=None, **data):
        try:
            report = request.env["ir.actions.report"]._get_report_from_name(reportname)
            
            context = dict(request.env.context)
            if docids:
                docids = [int(i) for i in docids.split(",")]
            if data.get("options"):
                data.update(json.loads(data.pop("options")))
            if data.get("context"):
                data["context"] = json.loads(data["context"])
                if data["context"].get("lang"):
                    del data["context"]["lang"]
                context.update(data["context"])

            xlsx_files, file_type = report.with_context(**context)._render_jinja_xlsx(reportname, docids, data=data)
            
            report_name = report.name
            filename = "%s.%s" % (report_name, "zip")
            if report.print_report_name and not len(docids) > 1:
                obj = request.env[report.model].browse(docids[0])
                report_name = safe_eval(report.print_report_name, {"object": obj})
                filename = "%s.%s" % (report_name, "xlsx")
            
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            if file_type == "zip":
                content_type = "application/zip"
                
            httpheaders = [
                ('Content-Type', content_type),
                ("Content-Length", len(xlsx_files)),
                ("Content-Disposition", content_disposition(filename))
            ]
            
            return request.make_response(xlsx_files, headers=httpheaders)

        except Exception as e:
            se = serialize_exception(e)
            error = {"code": 200, "message": "Odoo Server Error", "data": se}
            return request.make_response(html_escape(json.dumps(error)))