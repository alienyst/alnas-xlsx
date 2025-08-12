import os
import six
import logging
import subprocess
import tempfile
from io import BytesIO
from base64 import b64decode
from PIL import Image as PILImage, ImageFile

from xltpl.xlext import ImageRef
from odoo.tools.mimetypes import guess_mimetype


_logger = logging.getLogger(__name__)

def patch_init(self, image, image_index):
    self.image = image
    self.image_index = image_index
    self.rdrowx = -1
    self.rdcolx = -1
    self.wtrowx = -1
    self.wtcolx = -1

    if isinstance(image, bytes):
        try:
            imageb64 = b64decode(image)
            # Handle webp images, convert to png
            # i dont know why PIL cant read webp image from odoo binary field
            if imageb64 and guess_mimetype(imageb64, '') == 'image/webp':
                with tempfile.NamedTemporaryFile(delete=False, suffix='.webp') as temp_webp_file:
                    temp_webp_file.write(imageb64)
                    temp_webp_file_path = temp_webp_file.name

                temp_png_file_path = temp_webp_file_path.replace('.webp', '.png')
                subprocess.run(['dwebp', temp_webp_file_path, '-o', temp_png_file_path])

                with open(temp_png_file_path, 'rb') as f:
                    self.image = BytesIO(f.read())
                    
                os.remove(temp_webp_file_path)
                os.remove(temp_png_file_path)
                
            else:
                self.image = PILImage.open(BytesIO(imageb64))

        except Exception as error:
            _logger.error('Error processing image: %s', error)
            self.image = None
            
    elif not isinstance(image, ImageFile.ImageFile):
        fname = six.text_type(image)
        if not os.path.exists(fname):
            self.image = None

ImageRef.__init__ = patch_init
