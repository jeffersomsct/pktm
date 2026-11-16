"""
images/snapshot_saver.py
Responsavel por salvar snapshots em disco.

Organiza por table_id/hand_id pra preservar historico (cada mao tem sua
propria pasta, cada captura seu proprio arquivo -- nao sobrescreve).
"""
import re
import time
from pathlib import Path
from typing import Optional

from PIL import Image


def sanitize_filename(text: str) -> str:
    """Remove caracteres problematicos pra filename."""
    return re.sub(r'[\\/*?:"<>|\s]', '_', text)


class SnapshotSaver:
    """Salva snapshots organizados por sessao/mao."""

    def __init__(self, base_dir: str = "imgs"):
        self.base_dir = str(base_dir)
        Path(self.base_dir).mkdir(parents=True, exist_ok=True)

    def save(
        self,
        img: Image.Image,
        table_id: Optional[str] = None,
        hand_id: Optional[str] = None,
        tag: str = "raw",
        title: Optional[str] = None,
    ) -> str:
        """
        Salva a imagem.

        Estrutura de pastas:
            base_dir/<table_id>/<hand_id>/<ts>_<tag>.png
            (fallback se table_id/hand_id ausentes:
             base_dir/<safe_title>_<ts>.png)

        Args:
            img: PIL.Image a salvar.
            table_id: hash da TableSession.
            hand_id: ID da mao (do SwC).
            tag: 'preflop_start' | 'flop' | 'turn' | 'river' |
                 'hero_turn' | 'showdown' | 'raw'
            title: titulo bruto da janela (fallback).

        Returns:
            Caminho absoluto do arquivo salvo.
        """
        ts = int(time.time() * 1000)

        if table_id and hand_id:
            sub = Path(self.base_dir) / table_id / hand_id
            sub.mkdir(parents=True, exist_ok=True)
            file_path = sub / f"{ts}_{tag}.png"
        else:
            safe = sanitize_filename(title) if title else "unknown"
            file_path = Path(self.base_dir) / f"{safe}_{ts}.png"

        img.save(str(file_path))
        return str(file_path)
