import base64
import zipfile
from io import BytesIO
from xlsxtpl.writerx import BookWriter
from odoo import _, api, fields, models
from odoo.tools.safe_eval import safe_eval, time
from odoo.exceptions import ValidationError, MissingError

from ..tools import misc as misc_tools


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    report_type = fields.Selection(
        selection_add=[("xlsx-jinja", "XLSX Jinja")],
        ondelete={"xlsx-jinja": "cascade"},
    )
    
    report_xlsx_jinja_template = fields.Binary(string="Report XLSX Jinja Template")
    report_xlsx_jinja_template_name = fields.Char(string="Report XLSX Jinja Template Name")

    @api.constrains(
        "report_type", "report_xlsx_jinja_template", "report_xlsx_jinja_template_name"
    )
    def _check_report_type(self):
        for rec in self:
            if rec.report_type == "xlsx-jinja" and (
                not rec.report_xlsx_jinja_template
                or not (rec.report_xlsx_jinja_template_name or "").lower().endswith(".xlsx")
            ):
                raise ValidationError(_("Please upload a valid .xlsx template."))
            
    def _get_rendering_context_xlsxtpl(self):
        context = self.env["mail.render.mixin"]._render_eval_context()
        context.update({
            "spelled_out": misc_tools.spelled_out,
            "formatdate": misc_tools.formatdate,
            "convert_currency": misc_tools.convert_currency,
            "company": self.env.company,
            "lang": self.env.context.get("lang", "id_ID"),
            "sysdate": fields.Datetime.now(),
        })
        return context

    def _render_jinja_xlsx(self, report_ref, docids, data):
        report = self._get_report(report_ref)
        return report._render_xlsx_records(docids, data)

    def _render_xlsx_records(self, docids, data=None):
        self.ensure_one()
        if not self.report_xlsx_jinja_template:
            raise MissingError(_("No XLSX Jinja template found."))

        template = BytesIO(base64.b64decode(self.report_xlsx_jinja_template))
        doc_obj = self.env[self.model].browse(docids).with_context(bin_size=False)
        return self._render_xlsx_jinja_mode(
            template,
            doc_obj,
            data or {},
            self._get_rendering_context_xlsxtpl(),
            report_name=self.print_report_name,
        )
    
    def _render_xlsx_jinja_mode(self, template_path, doc_obj, data, context, report_name="report"):
        template = template_path.getvalue()
        xlsx_files = []

        for obj in doc_obj:
            writer = BookWriter(BytesIO(template))
            writer.set_jinja_globals(dir=dir, getattr=getattr)
            sheet_states = writer.sheet_resource_map.sheet_state_list
            if not sheet_states:
                raise MissingError(_("The XLSX template does not contain any worksheet."))

            for sheet_state in sheet_states:
                writer.render_sheet({
                    **context,
                    "docs": obj,
                    "data": data,
                    "sheet_name": sheet_state.name,
                    "tpl_idx": sheet_state.index,
                })

            output = BytesIO()
            writer.save(output)
            xlsx_files.append(output.getvalue())

        if len(xlsx_files) == 1:
            return xlsx_files[0], "xlsx"

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for idx, (obj, xlsx_file) in enumerate(zip(doc_obj, xlsx_files), start=1):
                name = (
                    safe_eval(report_name, {"object": obj, "time": time})
                    if report_name
                    else False
                )
                safe_filename = str(name or f"report_{idx}").replace("/", "_").replace("\\", "_")
                filename = f"{safe_filename}.xlsx"
                suffix = 2
                while filename in zip_file.namelist():
                    filename = f"{safe_filename}_{suffix}.xlsx"
                    suffix += 1
                zip_file.writestr(filename, xlsx_file)

        return zip_buffer.getvalue(), "zip"
