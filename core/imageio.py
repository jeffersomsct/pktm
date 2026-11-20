"""
core/imageio.py
Leitura e escrita de imagens que funcionam com caminhos nao-ASCII no Windows.

cv2.imread / cv2.imwrite falham EM SILENCIO (devolvem None / False) quando o caminho tem acento
(ex.: C:\\Users\\Joao\\...). Ler os bytes com numpy e decodificar com o OpenCV evita isso.
"""
from pathlib import Path

import cv2
import numpy as np


def read_image(path, flags: int = cv2.IMREAD_COLOR):
    """Imagem lida de `path` (BGR por padrao), ou None se nao existir ou nao decodificar."""
    try:
        data = np.fromfile(str(path), dtype=np.uint8)
    except OSError:
        return None
    return cv2.imdecode(data, flags) if data.size else None


def write_image(path, image) -> bool:
    """Grava `image` em `path` (o formato vem da extensao; PNG se nao houver). True se gravou;
    False (sem levantar) se a imagem for None/vazia ou nao puder ser codificada."""
    if image is None or getattr(image, "size", 0) == 0:
        return False
    path = Path(path)
    try:
        ok, encoded = cv2.imencode(path.suffix or ".png", image)
    except cv2.error:
        return False
    if not ok:
        return False
    encoded.tofile(str(path))
    return True
