import logging
from io import BytesIO
from base64 import b64decode

from PIL import Image as PILImage, WebPImagePlugin #to handle webp
from jinja2 import nodes

from xltpl.xlext import ImageRef, ImagexExtension, pil


_logger = logging.getLogger(__name__)
_origin_init = ImageRef.__init__

def _patched_image_ref_init(
    self,
    image,
    image_index,
    allow_insert=False,
    resize_mode="fit_cell",
    desired_width=0,
    desired_height=0,
):
    _origin_init(self, image, image_index)
    self.allow_insert = allow_insert
    self.resize_mode = resize_mode
    self.desired_width = desired_width
    self.desired_height = desired_height

    if isinstance(image, bytes):
        try:
            self.image = PILImage.open(BytesIO(b64decode(image)))
            if self.image.format == 'WEBP':
                # convert to png
                png_bytes = BytesIO()
                self.image.save(png_bytes, format='PNG')
                png_bytes.seek(0)
                self.image = PILImage.open(png_bytes)
                
        except Exception as exc:
            _logger.error("Error processing image: %s", exc)
            self.image = None

ImageRef.__init__ = _patched_image_ref_init
_orig_image_handler = ImagexExtension._image

def _patched_parse(self, parser):
    tag_token = parser.stream.current
    tag_name = tag_token.value
    lineno = next(parser.stream).lineno

    arg_nodes = []
    key_nodes = []
    value_nodes = []

    while parser.stream.current.type != "block_end":
        if (
            parser.stream.current.type == "name"
            and parser.stream.look().type == "assign"
        ):
            key_token = parser.stream.current
            parser.stream.skip()
            parser.stream.expect("assign")
            value_nodes.append(parser.parse_expression())
            key_nodes.append(nodes.Const(key_token.value))
        else:
            arg_nodes.append(parser.parse_expression())

        if not parser.stream.skip_if("comma"):
            break

    while parser.stream.skip_if("comma"):
        pass

    dict_items = [
        nodes.Pair(key, value) for key, value in zip(key_nodes, value_nodes)
    ]

    body = []
    return nodes.CallBlock(
        self.call_method(
            "_image",
            [
                nodes.Const(tag_name),
                nodes.List(arg_nodes, lineno=lineno),
                nodes.Dict(dict_items),
            ],
        ),
        [],
        [],
        body,
    ).set_lineno(lineno)


def _patched_image(self, tag_name, arg_list, kw_dict, caller):
    if not pil:
        return ""
        
    args = list(arg_list)
    kwargs = dict(kw_dict or {})
    image = args[0] if args else None
    image_index = 0
    
    if tag_name == "insert_img":
        image_ref = ImageRef(
            image,
            image_index,
            allow_insert=True,
            resize_mode="fit_cell",
        )
        if image_ref.image:
            node = self.environment.node_map.current_node
            node.set_image_ref(image_ref)
        return "image"

    elif tag_name == "insert_img_cell":
        width_arg = kwargs.pop("width", 0)
        height_arg = kwargs.pop("height", 0 )
        
        if width_arg is None and len(args) > 2:
            width_arg = args[2]
        if height_arg is None and len(args) > 3:
            height_arg = args[3]

        image_ref = ImageRef(
            image,
            image_index,
            allow_insert=True,
            resize_mode="resize_cell",
            desired_width=width_arg,
            desired_height=height_arg,
        )
        if image_ref.image:
            node = self.environment.node_map.current_node
            node.set_image_ref(image_ref)
        return "image"
    
    else:
        image_index = args[1] if len(args) > 1 else 0

    return _orig_image_handler(self, image, image_index, caller)

ImagexExtension.tags = {'img', 'insert_img', 'insert_img_cell'}
ImagexExtension.parse = _patched_parse
ImagexExtension._image = _patched_image