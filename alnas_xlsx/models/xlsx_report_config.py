from odoo import models, fields, api
from odoo.exceptions import UserError


class XlsxReportConfig(models.Model):
    _name = 'xlsx.report.config'
    _description = 'Xlsx Report Configuration'
    
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string='Report Name', required=True, readonly=True, states={"draft": [("readonly", False)]}, help="Name of the report")
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade', readonly=True, states={"draft": [("readonly", False)]}, help="Model to which this report will be attached")
    field_id = fields.Many2one('ir.model.fields', string='Field Name', required=True, ondelete='cascade', domain="[('model_id', '=', model_id),('ttype', '=', 'char')]", readonly=True, states={"draft": [("readonly", False)]}, help="Field to be used as the report name")
    report_xlsx_template = fields.Binary(string='Report XLSX Template', required=True, readonly=True, states={"draft": [("readonly", False)]}, help="xlsx template to be used for the report")
    report_xlsx_template_filename = fields.Char(string='Report XLSX Template Name', required=True, readonly=True, states={"draft": [("readonly", False)]})
    prefix = fields.Char(string='Prefix', readonly=True, states={"draft": [("readonly", False)]}, help="Prefix to be used in the report name")
    state = fields.Selection([('draft', 'Draft'),('published', 'Published')],
        string='State',
        default='draft',
        tracking=True,
        copy=False,
        readonly=True, states={"draft": [("readonly", False)]}
    )
    
    action_report_id = fields.Many2one('ir.actions.report', string='Related Report Action', readonly=True, copy=False)    
    print_report_name = fields.Char(string='Print Report Name', compute='_compute_print_report_name', help="Filename generated for the report")
            
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
            if not rec.report_xlsx_template_filename.endswith('.xlsx'):
                raise UserError('Please upload a xlsx template.')
    
    def _action_publish(self):
        for record in self:
            if record.state == 'draft':
                if not record.action_report_id:                
                    action_report = self.env['ir.actions.report'].sudo().create({
                        'name': record.name,
                        'model': record.model_id.model,
                        'report_type': 'xlsx-jinja',
                        'report_xlsx_jinja_template': record.report_xlsx_template,
                        'report_xlsx_jinja_template_name': record.report_xlsx_template_filename,
                        'report_name': record.report_xlsx_template_filename,
                        'print_report_name': record.print_report_name,
                    })
                else:
                    action_report = record.action_report_id
                    action_report.sudo().write({
                        'name': record.name,
                        'model': record.model_id.model,
                        'report_type': 'xlsx-jinja',
                        'report_xlsx_jinja_template': record.report_xlsx_template,
                        'report_xlsx_jinja_template_name': record.report_xlsx_template_filename,
                        'report_name': record.report_xlsx_template_filename,
                        'print_report_name': record.print_report_name,
                    })
                
                action_report.create_action()
                record.action_report_id = action_report
                record.state = 'published'
            else:
                raise UserError('Report already published')
        return True
    
    def action_publish(self):
        self._action_publish()
        return self._refresh_page()
    
    def _action_unpublish(self):
        for record in self:
            if record.state == 'published':
                record.action_report_id.unlink_action()
                record.state = 'draft'
            else:
                raise UserError('Report already unpublished')
        return True
    
    def action_unpublish(self):
        self._action_unpublish()
        return self._refresh_page()
            
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