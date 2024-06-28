# Xlsx Report Generator

The Xlsx Report Generator is a module that helps you create reports using only a .Xlsx template and Jinja syntax.

This module inspired from [Report Xlsx](https://apps.odoo.com/apps/modules/16.0/report_xlsx).

## Prerequisites

Before installing this module, make sure to install the following libraries:

- `pip install xlsxtpl num2words Babel`

## Usage

For usage instructions, you can refer to the following video: [Link](https://youtu.be/-mpE5AaSJhw)  
![Video Preview](assets/preview.gif)

Documentation on xlsxtpl syntax in the document: [Link](https://pypi.org/project/xlsxtpl/)
Example Template: [Link](https://github.com/alienyst/alnas-xlsx/raw/16.0/alnas_xlsx/static/description/example/example.xlsx)

## Field Naming Convention

To call and write the field name, use the following format: `{{docs.field_name}}`, starting with the word "docs".

### Useful Functions

- `{{spelled_out(docs.numeric_field)}}`: Spell out numbers
- `{{formatdate(docs.date_field)}}`: Format dates

Note: The functions will be updated as needed.

lang default is lang='id_ID' change if need, example = `{{spelled_out(docs.numeric_field, lang='en_US')}}`

## Feedback

We welcome any feedback and suggestions, especially for improving this module. Thank you!
