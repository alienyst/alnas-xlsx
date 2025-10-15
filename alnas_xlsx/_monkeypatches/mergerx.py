from math import floor

from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.utils import get_column_letter
from openpyxl.utils.units import points_to_pixels, pixels_to_EMU

from xltpl.mergerx import ImageMerger as _ImageMerger
from xltpl.mergerx import Merger as _Merger


DEFAULT_COLUMN_WIDTH = 8.43  # excel default character width
DEFAULT_ROW_HEIGHT = 15  # pt


def _patch_image_merger_set_image_ref(self, image_ref):
    merge = self._merge_map.get(image_ref.image_key)
    if not merge:
        return False
    merge.set_image_ref(image_ref)
    return True


def _patch_merger_set_image_ref(self, image_ref):
    handled = self.image_merger.set_image_ref(image_ref)
    if handled:
        return True

    if image_ref.allow_insert and image_ref.image:
        self._extra_images.append(image_ref)
        return True
    return False


def _column_width_to_pixels(width, sheet):
    width = width or sheet.sheet_format.defaultColWidth or DEFAULT_COLUMN_WIDTH
    return max(int(floor((width * 256 + 128) / 256 * 7)), 1)


def _row_height_to_pixels(height, sheet):
    height = height or sheet.sheet_format.defaultRowHeight or DEFAULT_ROW_HEIGHT
    return max(points_to_pixels(height), 1)


# insert image into worksheet
def _patch_merger_collect_range(self, wtsheet):
    self._orig_collect_range(wtsheet)
    extra_images = self._extra_images
    if not extra_images:
        return

    for image_ref in extra_images:
        img = image_ref.image
        if not img:
            continue

        row = image_ref.wtrowx or 1
        col = image_ref.wtcolx or 1
        col_letter = get_column_letter(col)

        col_dim = wtsheet.column_dimensions.get(col_letter)
        row_dim = wtsheet.row_dimensions.get(row)
        col_width = col_dim.width
        row_height = row_dim.height
        
        # resize image
        img = OpenpyxlImage(img)
        img.width = _column_width_to_pixels(col_width, wtsheet)
        img.height = _row_height_to_pixels(row_height, wtsheet)

        anchor = OneCellAnchor(
            _from=AnchorMarker(col=col, colOff=0, row=row-1 , rowOff=0),
            ext=XDRPositiveSize2D(
                pixels_to_EMU(img.width),
                pixels_to_EMU(img.height),
            ),
        )
        img.anchor = anchor
        wtsheet.add_image(img)

    extra_images.clear()


_Merger._extra_images = []
_Merger._orig_collect_range = _Merger.collect_range
_Merger.collect_range = _patch_merger_collect_range
_Merger.set_image_ref = _patch_merger_set_image_ref
_ImageMerger.set_image_ref = _patch_image_merger_set_image_ref
