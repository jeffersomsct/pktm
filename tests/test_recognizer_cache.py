"""
Garante que o cache por ROI do reconhecedor nunca devolve um valor velho.

Rodar da raiz do projeto:   python tests/test_recognizer_cache.py
Sai com codigo != 0 se alguma verificacao falhar.
"""
import contextlib
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)                          # os caminhos de templates do projeto sao relativos a raiz
sys.path.insert(0, str(ROOT))

import cv2
from config import room_config as rc
from poker_table_recognizer import TableAnalyzer

rc.RoomConfig.debug_mode = False

VERSIONS = {
    "get_swc_poker_config_v2": ["imgs/models/swc/v2/table_example.png",
                                "imgs/models/swc/v2/table_example-.png",
                                "imgs/models/swc/v2/table_example--.png"],
    "get_swc_poker_config_v3": ["imgs/models/swc/v3/table_example.png",
                                "imgs/models/swc/v3/table_example-.png",
                                "imgs/models/swc/v3/table_example---.png"],
}


def quiet():
    return contextlib.redirect_stdout(io.StringIO())


def snapshot(ti):
    """Tudo o que o reconhecedor produz, em forma comparavel."""
    return (ti.hand, ti.pot, ti.small_pot, ti.dealer_position,
            tuple(str(c) for c in ti.community_cards), tuple(ti.bb_positions),
            tuple((p.seat, p.name, p.stack, p.current_bet, p.is_present, p.is_active,
                   p.pos_preflop.value if p.pos_preflop else None) for p in ti.players))


def read(analyzer, img):
    with quiet():
        return snapshot(analyzer.analyze_table(img))


def fresh(config_fn):
    return TableAnalyzer(getattr(rc, config_fn)())          # analisador novo = sem nenhum cache


calls = {"n": 0}
_match_template = cv2.matchTemplate


def counting_match_template(*args, **kwargs):
    calls["n"] += 1
    return _match_template(*args, **kwargs)


cv2.matchTemplate = counting_match_template
checks = 0

for config_fn, paths in VERSIONS.items():
    imgs = [cv2.imread(p) for p in paths]
    assert all(im is not None for im in imgs), f"imagem de exemplo nao encontrada em {paths}"
    cold = [read(fresh(config_fn), im) for im in imgs]       # referencia: sem cache

    # 1) um unico analisador, imagens alternando: nada pode "vazar" de uma imagem para outra
    analyzer = fresh(config_fn)
    for rep in range(4):
        for i, im in enumerate(imgs):
            assert read(analyzer, im) == cold[i], f"{config_fn}: imagem {i} mudou na repeticao {rep}"
            checks += 1

    # 2) frame repetido: mesmo resultado e quase nenhum matchTemplate (so o detector de assento)
    analyzer = fresh(config_fn)
    read(analyzer, imgs[0])
    calls["n"] = 0
    assert read(analyzer, imgs[0]) == cold[0], f"{config_fn}: frame repetido mudou o resultado"
    seats = len(getattr(rc, config_fn)().player_detection_config.positions)
    assert calls["n"] == seats, f"{config_fn}: esperado {seats} matchTemplate no frame repetido, houve {calls['n']}"
    checks += 2

    # 3) altera UM ROI por vez (cola nele os pixels de outra imagem): so aquele ROI pode ser relido
    cfg = getattr(rc, config_fn)()
    rois = {**cfg.roi_config.stacks, **cfg.roi_config.names, **cfg.roi_config.bets,
            **cfg.roi_config.pot, **cfg.roi_config.smallpot}
    base, other = imgs[0], imgs[1]
    analyzer = fresh(config_fn)
    read(analyzer, base)                                     # aquece o cache com a imagem base
    for name, (x, y, w, h) in rois.items():
        mixed = base.copy()
        mixed[y:y + h, x:x + w] = other[y:y + h, x:x + w]
        assert read(analyzer, mixed) == read(fresh(config_fn), mixed), f"{config_fn}: ROI {name} ficou velho"
        read(analyzer, base)                                 # volta ao estado base
        checks += 1

print(f"OK: {checks} verificacoes, cache consistente.")
