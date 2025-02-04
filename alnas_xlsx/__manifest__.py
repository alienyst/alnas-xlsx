{
    'name': "XLSX Report Generator",

    'summary': """
        Generate your Report with Excel template""",

    'description': """
        Simple module to generate report with Excel template
    """,

    'author': "Ali Ns",
    'website': "https://github.com/alienyst",
    'images': ["static/description/banner.png"],
    'category': 'Technical',
    'version': '1.0',
    'application': True,
    'installable': True,

    'depends': ['base', 'mail'],

    'data': [
        'security/ir.model.access.csv',
        
        'views/xlsx_report_config_view.xml',
        
        'views/ir_action_report_view.xml',

        'views/webclient_templates.xml',
    ],

    'license': 'LGPL-3',    
    'external_dependencies': {
        'python': ['xlsxtpl'],
    }
    
}
