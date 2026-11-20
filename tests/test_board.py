"""
Board: cartas pareadas pela posicao, 10 lido como 'T' e glifo faltando sem desalinhar as outras.

Monta frames colando os glifos de rank/naipe do proprio repositorio sobre a amostra v3, NAS
POSICOES MEDIDAS NUMA MAO REAL (rank em (258+67k, 232), naipe em (258+67k, 257); cartas de 60x84
com o canto em (251+67k, 227)). Se alguem mexer nos ROIs do board e eles deixarem de cobrir o glifo,
este teste quebra. Valida geometria e pareamento, nao o desempenho do OCR em jogo real.

Rodar da raiz do projeto:   python tests/test_board.py
"""
import cv2
from _common import ROOT, analyze, load_sample
from core.imageio import read_image

_, SAMPLE = load_sample()
PITCH, RANK_Y, SUIT_Y, FIRST_X = 67, 232, 257, 258


def paste(frame, path, x, y):
    glyph = read_image(ROOT / path, cv2.IMREAD_GRAYSCALE)
    assert glyph is not None, path
    h, w = glyph.shape
    frame[y:y + h, x:x + w] = cv2.cvtColor(glyph, cv2.COLOR_GRAY2BGR)


def board_read(cards):
    """cards: lista de (arquivo do rank, arquivo do naipe); None em um dos lados = glifo ausente."""
    frame = SAMPLE.copy()
    for k, (rank_file, suit_file) in enumerate(cards):
        if rank_file:
            paste(frame, f"imgs/models/swc/v3/ranks/{rank_file}.png", FIRST_X + PITCH * k, RANK_Y)
        if suit_file:
            paste(frame, f"imgs/models/swc/v3/suits/{suit_file}.png", FIRST_X + PITCH * k, SUIT_Y)
    return [str(c) for c in analyze(frame, title=None).community_cards]


# Rio completo (a mao 305617200 da gravacao): 5h 4c 6h 6s 7s. Tem dois 6 em cartas diferentes.
assert board_read([("5", "H"), ("4", "C"), ("6", "H"), ("6", "S"), ("7", "S")]) == ["5H", "4C", "6H", "6S", "7S"]

# O 10 (arquivo 10.png) e lido como 'T'. Antes nao havia template e 5s Th Kd virava 5s Kh.
assert board_read([("5", "S"), ("10", "H"), ("K", "D")]) == ["5S", "TH", "KD"]

# Glifo faltando derruba so aquela carta; as outras ficam com o proprio naipe.
assert board_read([("5", "S"), (None, "H"), ("K", "D")]) == ["5S", "KD"]
assert board_read([("5", "S"), ("4", None), ("K", "D")]) == ["5S", "KD"]

# Mesa sem board: nada.
assert board_read([]) == []

print("OK: board lido nas posicoes medidas (5 cartas, 10, glifo faltando, vazio).")
