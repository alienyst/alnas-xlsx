from datetime import datetime
from num2words import num2words
from babel.dates import format_date
from babel.numbers import format_currency

# Formatting Function
def formatdate(date_required=datetime.today(), format="full", lang="id_ID", **kwargs):
    return format_date(date_required, format=format, locale=lang, **kwargs)

def spelled_out(number, lang="id_ID", to="cardinal", **kwargs):
    return num2words(number, lang=lang, to=to, **kwargs)

def convert_currency(number, currency_field, locale='id_ID', **kwargs):
    return format_currency(number, currency_field.name, locale=locale, **kwargs)