"""
Armazenamento: uma captura por numero de mao, sem sobrescrever a primeira; JSON legivel; e
leitura/escrita de PNG em caminho COM ACENTO (cv2.imread/imwrite falham em silencio no Windows).

Rodar da raiz do projeto:   python tests/test_capture_store.py
"""
import tempfile
from dataclasses import replace
from pathlib import Path

import numpy as np
from _common import SAMPLE_TITLE, analyze, load_sample
from core.imageio import read_image, write_image
from storage.capture_store import EXISTS, NO_HAND, SAVED, CaptureStore

_, image = load_sample()
table = analyze(image)

with tempfile.TemporaryDirectory(prefix="pktm_çãé_") as tmp:           # caminho com acento
    store = CaptureStore(Path(tmp) / "data")
    assert store.count() == 0

    # primeira captura da mao
    status, png = store.save(table, SAMPLE_TITLE, image)
    assert status == SAVED and png.name == "305616387.png" and png.is_file(), (status, png)
    first_bytes = png.read_bytes()
    assert np.array_equal(read_image(png), image)                       # round-trip com acento no caminho
    assert store.count() == 1

    record = store.get("305616387")
    assert record["title"] == SAMPLE_TITLE and record["snapshot_path"] == "snapshots/305616387.png"
    t = record["table"]
    assert t["hand"] == "305616387" and t["pot"] == 196.0 and t["small_pot"] == 56.0
    assert t["dealer_position"] == 7 and t["snapshot_path"] == "snapshots/305616387.png"
    assert (t["sb_amount"], t["bb_amount"], t["ante"]) == (20.0, 40.0, 8.0)
    seats = {p["seat"]: p for p in t["players"]}
    assert seats[6]["pos_preflop"] == "SB" and seats[5]["pos_preflop"] == "BB"   # Enum vira texto
    assert (seats[4]["name"], seats[4]["stack"], seats[4]["current_bet"]) == ("SaGiTaRiO25", 1862.0, 40.0)
    assert seats[1]["is_present"] is False
    assert store.get("999") is None

    # a mesma mao de novo NAO sobrescreve a primeira captura
    status, again = store.save(table, "outro titulo", (image // 2).astype(np.uint8))
    assert status == EXISTS and again == png and png.read_bytes() == first_bytes
    assert store.count() == 1 and store.get("305616387")["title"] == SAMPLE_TITLE

    # outra mao: nova linha (e tipos numpy nao quebram o JSON)
    status, _ = store.save(replace(table, hand="305616388", dealer_position=np.int64(3)), SAMPLE_TITLE, image)
    assert status == SAVED and store.count() == 2
    assert store.get("305616388")["table"]["dealer_position"] == 3

    # numero da mao nao lido: guarda so a imagem, em sem_mao/, e nao cria linha
    for unreadable in ("", "  ", "30x"):
        status, orphan = store.save(replace(table, hand=unreadable), SAMPLE_TITLE, image)
        assert status == NO_HAND and orphan.parent.name == "sem_mao" and orphan.is_file()
    assert store.count() == 2

    # um novo CaptureStore na mesma pasta enxerga o que ja foi gravado
    assert CaptureStore(Path(tmp) / "data").count() == 2

    # write_image devolve False (nao levanta) quando nao ha o que gravar...
    assert write_image(Path(tmp) / "vazia.png", np.zeros((0, 0, 3), np.uint8)) is False
    assert write_image(Path(tmp) / "nada.png", None) is False
    # ...e o save() falha ALTO, sem deixar uma linha no banco sem imagem (captura ao vivo que devolveu None)
    for broken in (None, np.zeros((0, 0, 3), np.uint8)):
        try:
            store.save(replace(table, hand="305616999"), SAMPLE_TITLE, broken)
        except OSError:
            pass
        else:
            raise AssertionError("save() deveria levantar OSError sem imagem")
    assert store.count() == 2 and store.get("305616999") is None

print("OK: uma captura por mao, sem sobrescrever; caminho com acento; JSON legivel.")
