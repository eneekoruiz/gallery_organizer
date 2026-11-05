"""Decode gallery images to BGR, including iPhone HEIF/HEIC originals."""
from io import BytesIO

import cv2
import numpy as np


def decode_image(data):
    encoded = np.frombuffer(data, dtype=np.uint8)
    if not encoded.size:
        return None
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image is not None:
        return image
    from PIL import Image, ImageOps, UnidentifiedImageError
    from pillow_heif import register_heif_opener
    register_heif_opener(thumbnails=False)
    try:
        with Image.open(BytesIO(data)) as photo:
            return cv2.cvtColor(np.asarray(ImageOps.exif_transpose(photo).convert('RGB')), cv2.COLOR_RGB2BGR)
    except (UnidentifiedImageError, OSError, ValueError):
        return None
