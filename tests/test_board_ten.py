"""
Board com um 10: o reconhecedor deve ler 5s Th Kd (antes, o K ficava com o naipe do 10).

Monta um frame sintetico colando os glifos de rank/naipe do proprio repositorio sobre uma
mesa de exemplo. Valida o mapeamento do 10 -> 'T', nao o desempenho do OCR em jogo real.

Rodar da raiz do projeto:   python tests/test_board_ten.py
"""
import contextlib
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

import cv2
from config import room_config as rc
from poker_table_recognizer import TableAnalyzer

rc.RoomConfig.debug_mode = False

cfg = rc.get_swc_poker_config_v3()
frame = cv2.imread("imgs/models/swc/v3/table_example.png")
rank_x, rank_y, _, _ = cfg.roi_config.ranks["rank"]
suit_x, suit_y, _, _ = cfg.roi_config.suits["suit"]


def paste(path, x, y):
    glyph = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    h, w = glyph.shape
    frame[y:y + h, x:x + w] = cv2.cvtColor(glyph, cv2.COLOR_GRAY2BGR)


PITCH = 67                                                   # distancia entre cartas no board
for i, (rank_file, suit_file) in enumerate([("5", "S"), ("10", "H"), ("K", "D")]):
    paste(f"imgs/models/swc/v3/ranks/{rank_file}.png", rank_x + PITCH * i, rank_y)
    paste(f"imgs/models/swc/v3/suits/{suit_file}.png", suit_x + PITCH * i, suit_y)

with contextlib.redirect_stdout(io.StringIO()):
    board = [str(c) for c in TableAnalyzer(cfg).analyze_table(frame).community_cards]

assert board == ["5S", "TH", "KD"], f"board lido: {board}"
print("OK: board com 10 lido corretamente:", board)
