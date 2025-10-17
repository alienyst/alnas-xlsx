from math import floor

from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.utils import get_column_letter
from openpyxl.utils.units import points_to_pixels, pixels_to_EMU, pixels_to_points

from xltpl.mergerx import Merger as _Merger


DEFAULT_COLUMN_WIDTH = 8.43  # excel default character width
DEFAULT_ROW_HEIGHT = 15  # pt


def _patch_set_image_ref(self, image_ref):
    self.image_merger.set_image_ref(image_ref)
    if image_ref.allow_insert and image_ref.image:
        self._extra_images.append(image_ref)

def _column_width_to_pixels(width, sheet):
    width = width or sheet.sheet_format.defaultColWidth or DEFAULT_COLUMN_WIDTH
    return max(int(floor((width * 256 + 128) / 256 * 7)), 1)

def _row_height_to_pixels(height, sheet):
    height = height or sheet.sheet_format.defaultRowHeight or DEFAULT_ROW_HEIGHT
    return max(points_to_pixels(height), 1)

def _pixels_to_column_width(pixels, sheet):
    if pixels is None or pixels <= 0:
        return sheet.sheet_format.defaultColWidth

    width = max(pixels / 7.0, 0.1)
    for _ in range(512):
        if _column_width_to_pixels(width, sheet) >= pixels:
            return round(width, 2)
        width += 0.05
    return round(width, 2)


def _patch_collect_range(self, wtsheet):
    self._orig_collect_range(wtsheet)
    extra_images = self._extra_images
    if not extra_images:
        return

    for image_ref in extra_images:
        if not image_ref.image:
            continue

        row = image_ref.wtrowx or 1
        col = image_ref.wtcolx or 1
        col_letter = get_column_letter(col)

        mode = image_ref.resize_mode
        img = OpenpyxlImage(image_ref.image)
        if mode == "resize_cell":
            desired_width = float(image_ref.desired_width)
            desired_height = float(image_ref.desired_height)
            width_px = int(round(desired_width or img.width))
            height_px = int(round(desired_height or img.height))
            width_px = max(width_px, 1)
            height_px = max(height_px, 1)

            img.width = width_px
            img.height = height_px
            col_dim = wtsheet.column_dimensions[col_letter]
            col_dim.width = _pixels_to_column_width(width_px, wtsheet)
            row_dim = wtsheet.row_dimensions[row]
            row_dim.height = pixels_to_points(height_px)
        else:
            col_dim = wtsheet.column_dimensions.get(col_letter)
            row_dim = wtsheet.row_dimensions.get(row)
            col_width = col_dim.width if col_dim else None
            row_height = row_dim.height if row_dim else None
            img.width = _column_width_to_pixels(col_width, wtsheet)
            img.height = _row_height_to_pixels(row_height, wtsheet)

        anchor = OneCellAnchor(
            _from=AnchorMarker(col=col, colOff=0, row=row - 1, rowOff=0),
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
_Merger.collect_range = _patch_collect_range
_Merger.set_image_ref = _patch_set_image_ref