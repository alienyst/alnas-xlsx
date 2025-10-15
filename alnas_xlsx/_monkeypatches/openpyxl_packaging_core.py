try:
    import datetime
    from openpyxl.packaging.core import NestedDateTime

    _original_to_tree = NestedDateTime.to_tree

    def _patched_to_tree(self, tagname=None, value=None, namespace=None):
        # patch for damage in odoo.sh (dcterms:modified has timezone)
        # remove timezone from value
        # https://github.com/alienyst/alnas-xlsx/issues/3
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        
        return _original_to_tree(self, tagname, value, namespace)

    NestedDateTime.to_tree = _patched_to_tree
    
except Exception as exc:
    import logging
    _logger = logging.getLogger(__name__)
    _logger.warning("Unable to patch openpyxl NestedDateTime: %s", exc)
