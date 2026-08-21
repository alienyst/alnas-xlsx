# Xlsx Report Generator

The Xlsx Report Generator is a module that helps you create reports using only a .Xlsx template and Jinja syntax.

This module inspired from [Report Xlsx](https://apps.odoo.com/apps/modules/16.0/report_xlsx).

## Prerequisites

Before installing this module, make sure to install the following libraries:

- `pip install xlsxjinja[image]`

Note: the `[image]` extra pulls in Pillow, which is required for the `{% img %}` and
`{% insert_img %}` tags. WebP binary fields from Odoo are converted automatically, so no
`dwebp` system package is needed.

## Usage

For security reasons, creating or editing XLSX Report Configurations is restricted to the **Report Editor** group (System Administrators by default). Regular users can only print published reports.

For usage instructions, you can refer to the following video: [Link](https://youtu.be/-mpE5AaSJhw)  
![Video Preview](assets/preview.gif)

Documentation on xlsxjinja syntax in the document: [Link](https://pypi.org/project/xlsxjinja/)
Example Template: [Link](https://github.com/alienyst/alnas-xlsx/raw/16.0/alnas_xlsx/static/description/example/example.xlsx)
Example Template with Image: [Link](https://github.com/alienyst/alnas-xlsx/raw/16.0/alnas_xlsx/static/description/example/example_with_picture.xlsx)

## Syntax & Templating Guide

This module uses [Jinja2](https://jinja.palletsprojects.com/) syntax parsed by the [xlsxjinja](https://pypi.org/project/xlsxjinja/) engine (a modern fork of `xltpl`). It natively understands Excel's grid layout, so you never write raw OOXML tags to duplicate rows or columns.

### 1. Variables
To print a field value, use the double curly braces format starting with `docs`:
- `{{ docs.name }}`
- `{{ docs.partner_id.name }}`

### 2. Looping with `{% tr %}` / `{% tc %}` (RECOMMENDED)
Put `{% tr %}` inside a cell value and the engine hoists the surrounding `for`/`if` tag to
row level, so **no empty row is left behind**.

* **Rows (`{% tr %}`)** — open in the first cell of the data row, close in the last cell:
  * `A2`: `{% tr %}{% for line in docs.order_line %}{{ line.name }}`
  * `B2`: `{{ line.product_uom_qty }}{% tr %}{% endfor %}`
* **Columns (`{% tc %}`)** — same idea, but repeats cells to the right:
  * `A1`: `{% tc %}{% for col in columns %}{{ col }}`
  * `B1`: `{{ col }}!{% tc %}{% endfor %}`

Rules: opening tags (`for`, `if`, `elif`, `else`) must sit at the **start** of the cell
value, closing tags (`endfor`, `endif`) at the **end**. Place `{% tr %}` before the opening
tag and after the closing tag.

### 3. Looping with cell comments (`beforerow`)
Use a **cell comment** (right-click -> New Note) when `{% tr %}` cannot express the layout:
* the loop row contains **merged cells**, or
* one `{% for %}` must span **several template rows** (e.g. Odoo `display_type` section rows).

Write the tag in the comment of the row's first cell:
```
beforerow{% for line in docs.order_line %}
```
and close it either in the comment of the row below (`beforerow{% endfor %}`) or at the end
of the last cell value. Available comment keys: `beforerow`, `beforecell`, `aftercell`.

| Scenario | `{% tr %}` | `beforerow` comment |
| --- | --- | --- |
| Simple row loop | yes | yes |
| Conditional row | yes | yes |
| Merged-cell row | no | yes |
| `for` spanning multiple template rows | no | yes |
| No Excel comment needed | yes | no |

### 4. Looping by plain text tags (leaves empty rows)
Typing `{% for %}` / `{% endfor %}` straight into cells still works, but the engine only
removes the *text* — the physical row or cell stays behind as a blank. Same row = horizontal
repeat, different rows = vertical repeat. Prefer `{% tr %}` or `beforerow` instead.

### 5. Conditionals (If/Else)
Standard Jinja `{% if %}` / `{% else %}` / `{% endif %}`, hoisted the same way as loops:
* **With `{% tr %}` (no empty row):** `{% tr %}{% if docs.state == 'done' %}TOTAL` ... `{{ docs.amount_total }}{% tr %}{% endif %}`
* **With comments (no empty row):** `beforerow{% if docs.state == 'done' %}` and `beforerow{% endif %}`
* **Plain text:** works, but leaves an empty row.

### 6. Images
* **`{% img docs.image_field %}` — replace a placeholder.** Put a dummy image in the
  template, then write the tag in the cell under its top-left corner. The dummy keeps its
  size and position; only the binary content is swapped.
* **`{% insert_img docs.image_field %}` — insert without a placeholder.** No dummy image
  needed; the picture is scaled to the target cell's column width and row height.
* Both accept an optional index for multiple images in one cell: `{% img docs.logo, 1 %}`.
* Accepted values: base64 `bytes` (normal Odoo binary field), `BytesIO`, or a PIL image.
  WebP is converted to PNG in-memory automatically.

![Replace Image Syntax](assets/assets/replace_image.png)

### 7. Advanced Tags (`xv`, `yn`)
* **`{% xv variable_name %}` (eXtract Value):** keeps the native Python/Excel type (number,
  date, boolean) instead of writing a string, so `=SUM()` and friends keep working on the
  rendered cells. Optional second argument indexes multiple `xv` values in one cell:
  `{% xv line.qty, 1 %}`.
* **`{% yn boolean_field %}` (Yes/No):** renders a checkbox — a Wingdings 2 checkmark when
  truthy, an empty box when falsy. Handy for `fields.Boolean`.

### 8. Available Functions & Variables

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
