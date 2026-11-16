# pixel_detector.py
import numpy as np
from typing import Dict, Tuple, Union
from enum import Enum


class ColorDistance(Enum):
    """Métricas de distância entre cores."""
    CHEBYSHEV = "chebyshev"  # max(|dr|, |dg|, |db|) — padrão
    EUCLIDEAN = "euclidean"  # sqrt(dr² + dg² + db²)
    MANHATTAN = "manhattan"  # |dr| + |dg| + |db|


def detect_pixels_in_window(
    img: np.ndarray,
    positions: Dict[int, Tuple[int, int]],
    ref_colors: Union[Dict[int, Tuple[int, int, int]], Tuple[int, int, int]],
    threshold: float = 15,
    window_size: Tuple[int, int] = (3, 3),
    distance_metric: ColorDistance = ColorDistance.CHEBYSHEV,
    min_matching_ratio: float = 0.6,
) -> Dict[int, bool]:
    """
    Detecta presença de cor numa janela ao redor de cada posição.
    
    Reutilizável para: dealer button, fichas, botões ativos, etc.
    
    Args:
        img: imagem BGR ou RGB (H, W, 3) como np.array
        positions: {id: (x, y)} coordenadas centrais
        ref_colors: cor de referência única ou {id: (r, g, b)} por posição
        threshold: tolerância máxima (interpretação depende da métrica)
        window_size: (w, h) da janela. Use (1, 1) para pixel único.
        distance_metric: como calcular a distância entre cores
        min_matching_ratio: proporção mínima de pixels que deve corresponder
    
    Returns:
        {id: True/False} indicando detecção
    """
    h_img, w_img = img.shape[:2]
    half_w, half_h = window_size[0] // 2, window_size[1] // 2
    references = _normalize_ref_colors(positions, ref_colors)
    results = {}
    
    for pos_id, (x, y) in positions.items():
        # Bounds seguros (clamp nas bordas)
        x0, x1 = max(0, x - half_w), min(w_img, x + half_w + 1)
        y0, y1 = max(0, y - half_h), min(h_img, y + half_h + 1)
        
        patch = img[y0:y1, x0:x1]
        if patch.size == 0:
            results[pos_id] = False
            continue
        
        pixels = patch.reshape(-1, 3).astype(float)
        ref = np.asarray(references[pos_id], dtype=float)
        differences = np.abs(pixels - ref)
        
        if distance_metric == ColorDistance.CHEBYSHEV:
            distances = np.max(differences, axis=1)
        elif distance_metric == ColorDistance.EUCLIDEAN:
            distances = np.linalg.norm(differences, axis=1)
        else:
            distances = np.sum(differences, axis=1)

        match_ratio = np.mean(distances <= threshold)
        results[pos_id] = match_ratio >= min_matching_ratio
    
    return results


def _normalize_ref_colors(
    positions: Dict[int, Tuple[int, int]],
    ref_color
) -> Dict[int, Tuple[int, int, int]]:
    """Aceita cor única ou dict por posição — flexibilidade para o caller."""
    if isinstance(ref_color, dict):
        return ref_color
    return {k: ref_color for k in positions}