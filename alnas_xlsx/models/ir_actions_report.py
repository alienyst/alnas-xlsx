import base64
from io import BytesIO
import zipfile
from xlsxtpl.writerx import BookWriter
from num2words import num2words
from babel.dates import format_date

from odoo import _, api, fields, models
from odoo.tools.safe_eval import safe_eval, time
from odoo.exceptions import ValidationError



class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    report_type = fields.Selection(
        selection_add=[("xlsx-jinja", "XLSX Jinja")],
        ondelete={"xlsx-jinja": "cascade"},
    )
    
    report_xlsx_jinja_template = fields.Binary(string="Report XLSX Jinja Template")
    report_xlsx_jinja_template_name = fields.Char(string="Report XLSX Jinja Template Name")

    @api.constrains("report_type")
    def _check_report_type(self):
        for rec in self:
            if (
                rec.report_type == "xlsx-jinja"
                and not rec.report_xlsx_jinja_template
                and not rec.report_xlsx_jinja_template_name.endswith(".xlsx")
            ):
                raise ValidationError(_("Please upload an XLSX Jinja template."))

    def _render_jinja_xlsx(self, report_ref, docids, data):
        report = self._get_report_from_name(report_ref)
        file_template = report.report_xlsx_jinja_template

        if not file_template:
            raise ValueError("No XLSX Jinja template found.")

        template = BytesIO(base64.b64decode(file_template))
        doc_obj = self.env[report.model].browse(docids)

        context = {
            "spelled_out": self._spelled_out,
            "formatdate": self._formatdate,
            "company": self.env.company,
            "lang": self._context.get("lang", "id_ID"),
            "sysdate": fields.Datetime.now(),
        }

        return self._render_xlsx_jinja_mode(template, doc_obj, data, context, report_name=report.print_report_name)
    
    def _render_xlsx_jinja_mode(self, template_path, doc_obj, data, context, report_name="report"):
        xlsx_files = []
        writer = BookWriter(template_path)
        writer.jinja_env.globals.update(dir=dir, getattr=getattr)
        zip_buffer = BytesIO()
        
        for idx, obj in enumerate(doc_obj):
            context = {**context, "docs": obj, "data": data}
            idx = writer.get_tpl_idx(context)
            sheet_name = writer.get_sheet_name(context)
            writer.render_sheet(context, sheet_name, idx)
            
            temp = BytesIO()
            writer.save(temp)
            temp.seek(0)
            xlsx_files.append(temp.read())


        if len(xlsx_files) == 1:
            return xlsx_files[0], "xlsx"
        else:
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for idx, xlsx_file in enumerate(xlsx_files):
                    name = safe_eval(report_name, {"object": doc_obj[idx], "time": time})
                    filename = "%s.%s" % (name, "xlsx")
                    zip_file.writestr(filename, xlsx_file)

            zip_buffer.seek(0)
            return zip_buffer.read(), "zip"

    # Render Function
    @staticmethod
    def _formatdate(date_required=fields.Datetime.today(), format="full", lang="id_ID"):
        return format_date(date_required, format=format, locale=lang)

    @staticmethod
    def _spelled_out(number, lang="id_ID"):
        return num2words(number, lang=lang)
