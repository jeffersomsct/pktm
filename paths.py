"""
paths.py
Caminhos do projeto, ancorados na RAIZ do repositorio e nao no diretorio de onde o programa foi
chamado. Antes, rodar de outra pasta dava "No snapshot provided and couldn't load sample image",
que escondia a causa (o caminho relativo "imgs/models/..." nao existia dali).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"          # saidas de execucao: banco, snapshots, imagem de debug
