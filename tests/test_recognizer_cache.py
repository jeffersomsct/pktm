"""
Garante que o cache por ROI do reconhecedor nunca devolve um valor velho.

Usa so a amostra v3 e variantes montadas a partir dela, para nao depender de outras versoes.

Rodar da raiz do projeto:   python tests/test_recognizer_cache.py
"""
import cv2
from _common import load_sample, quiet, snapshot
from poker_table_recognizer import TableAnalyzer

config, BASE = load_sample()
ROIS = {**config.roi_config.stacks, **config.roi_config.names, **config.roi_config.bets,
        **config.roi_config.pot, **config.roi_config.smallpot, **config.roi_config.hand}


def read(analyzer, image):
    with quiet():
        return snapshot(analyzer.analyze_table(image))


def fresh():
    return TableAnalyzer(config)                      # analisador novo = sem nenhum cache


def copy_roi(dst, src, roi):
    x, y, w, h = roi
    dst[y:y + h, x:x + w] = src[y:y + h, x:x + w]


# Variantes distintas da mesma mesa: B troca as placas dos assentos 3 e 6; C esvazia o assento 4.
variant_b = BASE.copy()
for kind in ("stack", "name", "bet"):
    a, b = ROIS[f"{kind}_3"], ROIS[f"{kind}_6"]
    assert a[2:] == b[2:]                                       # mesmo tamanho: da para trocar
    x3, y3, w, h = a
    x6, y6, _, _ = b
    variant_b[y3:y3 + h, x3:x3 + w] = BASE[y6:y6 + h, x6:x6 + w]
    variant_b[y6:y6 + h, x6:x6 + w] = BASE[y3:y3 + h, x3:x3 + w]
variant_c = BASE.copy()
for kind in ("stack", "name"):
    x4, y4, w, h = ROIS[f"{kind}_4"]
    x1, y1, _, _ = ROIS[f"{kind}_1"]
    variant_c[y4:y4 + h, x4:x4 + w] = BASE[y1:y1 + h, x1:x1 + w]   # assento 1 esta vazio: so feltro

variants = [BASE, variant_b, variant_c]
cold = [read(fresh(), v) for v in variants]
assert len({c for c in cold}) == 3, "as variantes precisam dar leituras diferentes para o teste valer"
checks = 0

# 1) um unico analisador, variantes alternando: nada pode "vazar" de uma imagem para outra
analyzer = fresh()
for rep in range(4):
    for i, image in enumerate(variants):
        assert read(analyzer, image) == cold[i], f"variante {i} mudou na repeticao {rep}"
        checks += 1

# 2) frame repetido: mesmo resultado e NENHUM matchTemplate (tudo vem do cache)
calls = {"n": 0}
_match_template = cv2.matchTemplate


def counting_match_template(*args, **kwargs):
    calls["n"] += 1
    return _match_template(*args, **kwargs)


cv2.matchTemplate = counting_match_template
analyzer = fresh()
read(analyzer, BASE)
calls["n"] = 0
assert read(analyzer, BASE) == cold[0]
assert calls["n"] == 0, f"esperado 0 matchTemplate no frame repetido, houve {calls['n']}"
checks += 2
cv2.matchTemplate = _match_template

# 3) altera UM ROI por vez (cola nele os pixels da variante B): so aquele ROI pode ser relido
analyzer = fresh()
read(analyzer, BASE)
for name, roi in ROIS.items():
    mixed = BASE.copy()
    copy_roi(mixed, variant_b, roi)
    assert read(analyzer, mixed) == read(fresh(), mixed), f"ROI {name} ficou velho"
    read(analyzer, BASE)                                          # volta ao estado base
    checks += 1

print(f"OK: {checks} verificacoes, cache consistente.")
