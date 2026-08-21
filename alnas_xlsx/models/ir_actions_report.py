import base64
import logging
import os
import shutil
import subprocess
import tempfile
import zipfile
from io import BytesIO
from xlsxjinja import BookWriter
from odoo import _, api, fields, models
from odoo.tools.safe_eval import safe_eval, time
from odoo.exceptions import ValidationError, MissingError, UserError

from ..tools import misc as misc_tools

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    report_type = fields.Selection(
        selection_add=[("xlsx-jinja", "XLSX Jinja")],
        ondelete={"xlsx-jinja": "cascade"},
    )
    
    report_xlsx_jinja_template = fields.Binary(string="Report XLSX Jinja Template")
    report_xlsx_jinja_template_name = fields.Char(string="Report XLSX Jinja Template Name")
    xlsx_merge_mode = fields.Selection(
        [("single", "Single / Auto"), ("zip", "Zip"), ("pdf", "PDF")],
        string="XLSX Mode",
        default="single",
    )

    @api.constrains("report_type", "report_xlsx_jinja_template", "report_xlsx_jinja_template_name")
    def _check_report_type(self):
        for rec in self:
            if rec.report_type == "xlsx-jinja" and (
                not rec.report_xlsx_jinja_template
                or not (rec.report_xlsx_jinja_template_name or "").lower().endswith(".xlsx")
            ):
                raise ValidationError(_("Please upload a valid .xlsx template."))
            
    def _get_rendering_context_xlsx(self):
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

    def _render_xlsx_records(self, docids, data=None, merge_mode=None):
        self.ensure_one()
        if not self.report_xlsx_jinja_template:
            raise MissingError(_("No XLSX Jinja template found."))

        template = BytesIO(base64.b64decode(self.report_xlsx_jinja_template))
        doc_obj = self.env[self.model].browse(docids).with_context(bin_size=False)
        context = self._get_rendering_context_xlsx()
        mode = merge_mode or self.xlsx_merge_mode

        if mode == "pdf":
            return self._render_xlsx_to_pdf_mode(template, doc_obj, data or {}, context, report_name=self.print_report_name)
        elif mode == "zip":
            return self._render_xlsx_zip_mode(template, doc_obj, data or {}, context, report_name=self.print_report_name)
        else:
            return self._render_xlsx_single_mode(template, doc_obj, data or {}, context, report_name=self.print_report_name)

    def _render_single_workbook(self, template_bytes, obj, data, context):
        writer = BookWriter(BytesIO(template_bytes))
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
        return output.getvalue()

    def _render_xlsx_single_mode(self, template_path, doc_obj, data, context, report_name="report"):
        template_bytes = template_path.getvalue()
        xlsx_files = [self._render_single_workbook(template_bytes, obj, data, context) for obj in doc_obj]

        if len(xlsx_files) == 1:
            return xlsx_files[0], "xlsx"
        else:
            return self._create_zip_archive(xlsx_files, doc_obj, report_name, ext="xlsx")

    def _render_xlsx_zip_mode(self, template_path, doc_obj, data, context, report_name="report"):
        template_bytes = template_path.getvalue()
        xlsx_files = [self._render_single_workbook(template_bytes, obj, data, context) for obj in doc_obj]
        return self._create_zip_archive(xlsx_files, doc_obj, report_name, ext="xlsx")

    def _render_xlsx_to_pdf_mode(self, template_path, doc_obj, data, context, report_name="report"):
        template_bytes = template_path.getvalue()
        xlsx_files = [self._render_single_workbook(template_bytes, obj, data, context) for obj in doc_obj]

        if not xlsx_files:
            return b"", "pdf"

        temp_dir = tempfile.mkdtemp()
        try:
            pdf_files = []
            for idx, xlsx_data in enumerate(xlsx_files, start=1):
                xlsx_path = os.path.join(temp_dir, f"document_{idx}.xlsx")
                with open(xlsx_path, "wb") as f:
                    f.write(xlsx_data)

                pdf_path = self.convert_file_to_pdf(xlsx_path, temp_dir)
                if not pdf_path or not os.path.exists(pdf_path):
                    raise UserError(_("PDF conversion failed."))

                with open(pdf_path, "rb") as f:
                    pdf_files.append(f.read())

            if len(pdf_files) == 1:
                return pdf_files[0], "pdf"
            else:
                return self._create_zip_archive(pdf_files, doc_obj, report_name, ext="pdf")
        finally:
            shutil.rmtree(temp_dir)

    def _create_zip_archive(self, file_contents, doc_obj, report_name, ext="xlsx"):
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for idx, (obj, content) in enumerate(zip(doc_obj, file_contents), start=1):
                name = (
                    safe_eval(report_name, {"object": obj, "time": time})
                    if report_name
                    else False
                )
                safe_filename = str(name or f"report_{idx}").replace("/", "_").replace("\\", "_")
                filename = f"{safe_filename}.{ext}"
                suffix = 2
                while filename in zip_file.namelist():
                    filename = f"{safe_filename}_{suffix}.{ext}"
                    suffix += 1
                zip_file.writestr(filename, content)
        return zip_buffer.getvalue(), "zip"

    def convert_file_to_pdf(self, file_path, output_dir):
        librepath = self._get_libreoffice_path()
        profile_dir = os.path.join(output_dir, "lo_profile")

        command = [
            librepath,
            "--headless",
            "--invisible",
            "--nologo",
            "--nodefault",
            "--norestore",
            "--nolockcheck",
            "--nofirststartwizard",
            f"-env:UserInstallation=file://{profile_dir}",
            "--convert-to", "pdf",
            "--outdir", output_dir,
            file_path,
        ]

        env = os.environ.copy()
        env["SAL_DISABLE_OPENCL"] = "1"

        try:
            result = subprocess.run(command, env=env, timeout=120, capture_output=True, text=True)
            if result.returncode != 0:
                _logger.error("LibreOffice PDF conversion failed.\nSTDOUT: %s\nSTDERR: %s", result.stdout, result.stderr)
                raise UserError(f"PDF conversion failed (exit code {result.returncode}). Check logs for details.\nSTDERR: {result.stderr.strip()[-200:]}")
        except subprocess.TimeoutExpired as e:
            _logger.error("LibreOffice PDF conversion timed out.\nSTDOUT: %s\nSTDERR: %s", e.stdout, e.stderr)
            raise UserError(_("PDF conversion timed out."))
        except Exception as e:
            if isinstance(e, UserError):
                raise
            _logger.exception("LibreOffice PDF conversion exception.")
            raise UserError(f"PDF conversion error: {str(e)}")

        pdf_file_name = os.path.splitext(os.path.basename(file_path))[0] + ".pdf"
        pdf_file_path = os.path.join(output_dir, pdf_file_name)
        return pdf_file_path if os.path.exists(pdf_file_path) else None

    def _get_libreoffice_path(self):
        libreoffice = self.env.ref("alnas_xlsx.default_libreoffice_path", raise_if_not_found=False)
        if not libreoffice or not libreoffice.value:
            raise ValidationError(
                _("LibreOffice path does not exist.\nPlease set in Settings => Technical => Parameters => System Parameters => alnas_xlsx.default_libreoffice_path")
            )
        return libreoffice.value


