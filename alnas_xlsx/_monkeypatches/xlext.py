from xltpl.xlext import ImageRef

import base64
import io
import os
import six
from PIL import Image as PILImage, ImageFile


def patch_init(self, image, image_index):
    self.image = image
    self.image_index = image_index
    self.rdrowx = -1
    self.rdcolx = -1
    self.wtrowx = -1
    self.wtcolx = -1

    if isinstance(image, bytes):
        try:
            self.image = PILImage.open(io.BytesIO(base64.b64decode(image)))
        except Exception:
            self.image = None
            
    elif not isinstance(image, ImageFile.ImageFile):
        fname = six.text_type(image)
        if not os.path.exists(fname):
            self.image = None


ImageRef.__init__ = patch_init