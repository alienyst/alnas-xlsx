from odoo import _, api, fields, models
from odoo.exceptions import UserError


class XlsxReportConfig(models.Model):
    _name = 'xlsx.report.config'
    _description = 'Xlsx Report Configuration'
    
    _inherit = ["mail.thread", "mail.activity.mixin"]

    _report_code_name_unique = models.Constraint(
        "UNIQUE(report_name)",
        'Report code name must be unique!.',
    )

    name = fields.Char(
        string='Report Name', 
        required=True, 
        readonly=True, 
        help="Name of the report"
    )
    report_name = fields.Char(
        string="Report Code",
        required=True,
        copy=False,
        help="Report Unique Code use for Technical Purpose"
    )
    model_id = fields.Many2one(
        'ir.model', 
        string='Model', 
        required=True, 
        ondelete='cascade', 
        readonly=True, 
        help="Model to which this report will be attached"
    )
    model_name = fields.Char(compute="_compute_model_name", store=False)
    field_id = fields.Many2one(
        'ir.model.fields', 
        string='Field Name', 
        required=True, 
        ondelete='cascade', 
        domain="[('model_id', '=', model_id),('ttype', '=', 'char')]", 
        readonly=True, 
        help="Field to be used as the report name"
    )
    report_xlsx_template = fields.Binary(
        string='Report XLSX Template', 
        required=True, 
        readonly=True, 
        help="xlsx template to be used for the report"
    )
    report_xlsx_template_filename = fields.Char(
        string='Report XLSX Template Name', 
        required=True, 
        readonly=True
    )
    prefix = fields.Char(
        string='Prefix', 
        readonly=True, 
        help="Prefix to be used in the report name"
    )
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('published', 'Published')],
        string='State',
        default='draft',
        tracking=True,
        copy=False,
        readonly=True
    )
    
    action_report_id = fields.Many2one(
        'ir.actions.report', 
        string='Related Report Action', 
        readonly=True, 
        copy=False
    )    
    xlsx_merge_mode = fields.Selection(
        [("single", "Single / Auto"), ("zip", "Zip"), ("pdf", "PDF")],
        string="XLSX Merge Mode",
        default="single",
        required=True,
        readonly=True,
        help="Mode to be used for generating the report:\n \
            - 'Single / Auto': Returns XLSX directly (or ZIP if multiple records).\n \
            - 'Zip': Always generates a ZIP file containing multiple XLSX files.\n \
            - 'PDF': Converts the rendered XLSX (including all sheets) to PDF using LibreOffice.",
    )
    print_report_name = fields.Char(
        string='Print Report Name',
        compute='_compute_print_report_name',
        store=True,
        readonly=False,
        precompute=True,
        help="Filename expression for the generated report. "
        "Auto-filled from model/field/prefix; can be overridden manually."
    )
    domain = fields.Char(
        string="Filter Domain",
        help="If set, the report action will only appear on records that match this domain."
    )

    def copy_data(self, default=None):
        """Keep unique labels and report code when duplicating."""
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for record, vals in zip(self, vals_list):
            if "name" not in default:
                vals["name"] = _("%s (copy)", record.name)
            if "report_name" not in default:
                vals["report_name"] = _("%s (copy)", record.report_name)
        return vals_list

    @api.onchange("model_id")
    def _onchange_model_id(self):
        if not self.model_id:
            self.field_id = False
            return
        if self.field_id and self.field_id.model_id == self.model_id:
            return
        self.field_id = self._get_default_field_id(self.model_id)

    @api.depends("model_id")
    def _compute_model_name(self):
        for record in self:
            record.model_name = record.model_id.model or ""

    @api.depends('model_id', 'field_id', 'prefix')
    def _compute_print_report_name(self):
        for rec in self:
            if rec.prefix:
                rec.print_report_name = f"'{rec.prefix} %s' % object.{rec.field_id.name} if object.{rec.field_id.name} else ''"
            else:
                rec.print_report_name = f"'{rec.model_id.name} %s' % object.{rec.field_id.name} if object.{rec.field_id.name} else ''"
    
    @api.constrains('report_xlsx_template_filename')
    def _check_report_xlsx_template_filename(self):
        for rec in self:
            if not (rec.report_xlsx_template_filename or "").lower().endswith('.xlsx'):
                raise UserError('Please upload an XLSX template.')
    
    def _action_publish(self):
        for record in self:
            if record.state == 'draft':
                val = record._prepare_action_val()
                if not record.action_report_id:
                    action_report = self.env['ir.actions.report'].sudo().create(val)
                else:
                    action_report = record.action_report_id
                    action_report.sudo().write(val)
                
                action_report.create_action()
                record.action_report_id = action_report
                record.state = 'published'
        return True
    
    def action_publish(self):
        self._action_publish()
        return self._refresh_page()
    
    def _action_unpublish(self):
        for record in self:
            if record.state == 'published':
                record.action_report_id.sudo().unlink_action()
                record.state = 'draft'
        return True
    
    def action_unpublish(self):
        self._action_unpublish()
        return self._refresh_page()

    def _prepare_action_val(self):
        return {
            "name": self.name,
            "model": self.model_id.model,
            "report_type": "xlsx-jinja",
            "report_xlsx_jinja_template": self.report_xlsx_template,
            "report_xlsx_jinja_template_name": self.report_xlsx_template_filename,
            "report_name": self.report_name,
            "xlsx_merge_mode": self.xlsx_merge_mode,
            "print_report_name": self.print_report_name,
            "domain": self.domain or False,
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_xlsx_report(self):
        for rec in self:
            if rec.state == 'published':
                rec.action_unpublish()
            if rec.action_report_id:
                rec.action_report_id.unlink()
                
    def _refresh_page(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _get_default_field_id(self, model_id):
        """Prefer display_name, then model rec_name, then name."""
        Field = self.env["ir.model.fields"]
        if not model_id:
            return Field
        domain = [("model_id", "=", model_id.id), ("ttype", "=", "char")]
        field = Field.search(domain + [("name", "=", "display_name")], limit=1)
        if field:
            return field
        if model_id.model in self.env:
            rec_name = self.env[model_id.model]._rec_name
            if rec_name:
                field = Field.search(domain + [("name", "=", rec_name)], limit=1)
                if field:
                    return field
        return Field.search(domain + [("name", "=", "name")], limit=1)