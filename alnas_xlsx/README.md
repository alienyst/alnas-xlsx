# Xlsx Report Generator

The Xlsx Report Generator is a module that helps you create reports using only a .Xlsx template and Jinja syntax.

This module inspired from [Report Xlsx](https://apps.odoo.com/apps/modules/16.0/report_xlsx).

## Prerequisites

Before installing this module, make sure to install the following libraries:

- `pip install xlsxtpl`

Note: If you want to use replace image, please install webp
- `sudo apt install webp`

## Usage

For security reasons, creating or editing XLSX Report Configurations is restricted to the **Report Editor** group (System Administrators by default). Regular users can only print published reports.

For usage instructions, you can refer to the following video: [Link](https://youtu.be/-mpE5AaSJhw)  
![Video Preview](assets/preview.gif)

Documentation on xlsxtpl syntax in the document: [Link](https://pypi.org/project/xlsxtpl/)
Example Template: [Link](https://github.com/alienyst/alnas-xlsx/raw/16.0/alnas_xlsx/static/description/example/example.xlsx)
Example Template with Image: [Link](https://github.com/alienyst/alnas-xlsx/raw/16.0/alnas_xlsx/static/description/example/example_with_picture.xlsx)

## Syntax & Templating Guide

This module uses [Jinja2](https://jinja.palletsprojects.com/) syntax parsed by the [xlsxtpl / xltpl](https://pypi.org/project/xlsxtpl/) engine. It natively understands Excel's grid layout, meaning you do not need complex XML tags (like `<w:tr>`) to duplicate rows or columns.

### 1. Variables
To print a field value, use the double curly braces format starting with `docs`:
- `{{ docs.name }}`
- `{{ docs.partner_id.name }}`

### 2. Looping (Standard Method - Leaves Empty Rows/Cells)
If you type Jinja tags directly into Excel cells, the engine evaluates them, removes the text, but **leaves the empty physical cell/row** behind.
* **Vertical Loop (Rows):** Place `{% for line in docs.line_ids %}` in one row (e.g., A2), the variables in the next row (e.g., A3), and `{% endfor %}` in the row below that (e.g., A4). The engine will duplicate the rows vertically.
* **Horizontal Loop (Columns):** Place `{% for col in columns %}`, variables, and `{% endfor %}` **in the same row** (e.g., A2, B2, C2). The engine will duplicate the cells horizontally to the right.

### 3. Looping (Comment Technique - RECOMMENDED)
To perfectly loop rows or columns **without leaving empty rows or cells**, use Excel's **Cell Comments (Notes)** instead of typing tags into the cells!
* **Looping Rows without gaps:** 
  1. Click the first data cell (e.g., A2). Right-click -> **Insert Comment** (or New Note).
  2. Write exactly: `beforerow{% for line in docs.line_ids %}`
  3. Click the cell right below the data row (e.g., A3). Insert Comment.
  4. Write exactly: `beforerow{% endfor %}`
  *(The engine extracts these comments to bound the row, leaving no empty spaces behind!)*
* **Looping Columns without gaps:**
  Use `beforecell{% for col in columns %}` and `aftercell{% endfor %}` inside cell comments.

### 4. Conditionals (If/Else)
You can conditionally hide rows or columns using standard Jinja `{% if %}`.
* **Via Comments (No empty rows):** Put `beforerow{% if docs.state == 'done' %}` in the comment of the row you want to hide, and `beforerow{% endif %}` in the comment of the row right below it.
* **Via Text:** Type `{% if docs.state == 'done' %}` directly into the cell (leaves an empty row).

### 5. Inserting Images
To replace an image dynamically:
1. Insert a **dummy image** into your Excel template and position it exactly where you want it.
2. In the Excel cell **located exactly behind/under** the top-left corner of the dummy image, type:
   `{% img docs.image_binary_field %}`
*(The engine will find the image overlapping this cell and replace its binary content).*

![Replace Image Syntax](assets/assets/replace_image.png)

### 6. Advanced Tags (`xv`, `yn`)
The engine provides a few advanced internal tags for precise Excel manipulations:
* **`{% xv variable_name %}` (eXtract Value):** Extracts the variable while strictly preserving its original Excel data type (e.g., Number, Float, Boolean). Unlike `{{ variable_name }}` which often forces the output into a string, `xv` ensures the output remains a native number in Excel so formulas like `=SUM()` work perfectly on the rendered cells.
* **`{% yn boolean_variable %}` (Yes/No):** A specialized tag for rendering Checkboxes. If the variable is True, it prints a Wingdings 2 checkmark (☑). If False, it prints a square (□). This is great for boolean fields in Odoo.

### 7. Available Functions & Variables

**Odoo Native Context (Odoo 17+):**
- `user`: Current user (`{{ user.name }}`)
- `company`: Current company (`{{ company.name }}`)
- `sysdate`: Current system datetime
- `{{ format_date(docs.date_field) }}`: Format dates natively via Odoo's render context
- `{{ format_datetime(docs.datetime_field) }}`: Format datetime (timezone-aware)
- `{{ format_time(docs.datetime_field) }}`: Format time natively
- `{{ format_amount(docs.amount, docs.currency_id) }}`: Format monetary amounts with currency symbol natively
- `{{ format_duration(docs.duration_field) }}`: Format duration natively

**Custom Addon Functions:**
- `{{ spelled_out(docs.numeric_field) }}`: Spell out numbers (e.g., `lang='en_US'` or default `id_ID`).
- `{{ formatdate(docs.date_field) }}`: (Legacy) Format dates via babel.
- `{{ convert_currency(docs.monetary_field, docs.currency_id) }}`: (Legacy) Format monetary field via babel.

Note: The functions will be updated as needed.

## Feedback

We welcome any feedback and suggestions, especially for improving this module. Thank you!
