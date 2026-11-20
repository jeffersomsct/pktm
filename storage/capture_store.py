"""
storage/capture_store.py
Guarda UMA captura por numero de mao: a leitura da mesa (JSON, no SQLite) e o PNG da captura.

Nao ha hash nem identificacao de mesa: a chave e o numero da mao que o reconhecedor ja le (a SwC
numera as maos globalmente). Capturar a mesma mao outra vez NAO sobrescreve a primeira captura.

    data/pktm.db                  tabela captures (uma linha por mao)
    data/snapshots/<mao>.png      a imagem que originou a leitura
    data/snapshots/sem_mao/...    capturas em que o numero da mao nao foi lido (para depurar o OCR)
"""
import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

from core.imageio import write_image
from core.models import TableInfo
from paths import DATA_DIR

SAVED, EXISTS, NO_HAND = "saved", "exists", "no_hand"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS captures (
    hand_id       TEXT PRIMARY KEY,
    captured_at   TEXT NOT NULL,
    title         TEXT,
    snapshot_path TEXT,
    data          TEXT NOT NULL
)
"""


def _json_default(obj):
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, np.generic):
        return obj.item()
    raise TypeError(f"{type(obj).__name__} nao serializavel")


def table_to_json(table: TableInfo) -> str:
    """TableInfo -> JSON. Dataclasses aninhadas (Player, Card...) saem de graca com asdict."""
    return json.dumps(asdict(table), default=_json_default, ensure_ascii=False)


class CaptureStore:
    def __init__(self, root=DATA_DIR):
        self.root = Path(root)
        (self.root / "snapshots").mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "pktm.db"
        with self._db() as conn:
            conn.execute(_SCHEMA)

    @contextmanager
    def _db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:                      # commit (ou rollback se der erro)
                yield conn
        finally:
            conn.close()

    @staticmethod
    def _write_png(path: Path, image) -> None:
        """Perder uma captura em silencio e o pior caso da coleta: se nao der para gravar, levanta."""
        if not write_image(path, image):
            raise OSError(f"nao consegui gravar a imagem da captura em {path} (imagem vazia ou caminho invalido)")

    def save(self, table: TableInfo, title: Optional[str], image: np.ndarray) -> Tuple[str, Path]:
        """
        Grava a captura. Devolve (status, caminho do PNG):
          SAVED    primeira captura desta mao: PNG e linha gravados;
          EXISTS   essa mao ja estava gravada: nada foi alterado;
          NO_HAND  o numero da mao nao foi lido: so o PNG e gravado, em snapshots/sem_mao/.
        Levanta OSError se a imagem nao puder ser gravada (nada e inserido no banco).
        """
        hand_id = (table.hand or "").strip()
        if not hand_id.isdigit():
            path = self.root / "snapshots" / "sem_mao" / f"{int(time.time() * 1000)}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            self._write_png(path, image)
            return NO_HAND, path

        relative = Path("snapshots") / f"{hand_id}.png"
        with self._db() as conn:
            if conn.execute("SELECT 1 FROM captures WHERE hand_id = ?", (hand_id,)).fetchone():
                return EXISTS, self.root / relative
            self._write_png(self.root / relative, image)       # antes da linha: sem imagem nao ha captura
            stored = replace(table, snapshot_path=relative.as_posix())
            conn.execute(
                "INSERT INTO captures (hand_id, captured_at, title, snapshot_path, data) VALUES (?, ?, ?, ?, ?)",
                (hand_id, datetime.now().isoformat(timespec="seconds"), title,
                 relative.as_posix(), table_to_json(stored)),
            )
        return SAVED, self.root / relative

    def get(self, hand_id) -> Optional[dict]:
        """A captura da mao como dict (a leitura da mesa em 'table'), ou None."""
        with self._db() as conn:
            row = conn.execute(
                "SELECT hand_id, captured_at, title, snapshot_path, data FROM captures WHERE hand_id = ?",
                (str(hand_id),),
            ).fetchone()
        if row is None:
            return None
        return {"hand_id": row[0], "captured_at": row[1], "title": row[2],
                "snapshot_path": row[3], "table": json.loads(row[4])}

    def count(self) -> int:
        with self._db() as conn:
            return conn.execute("SELECT COUNT(*) FROM captures").fetchone()[0]
