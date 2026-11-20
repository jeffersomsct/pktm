"""
O reconhecedor funciona a partir de QUALQUER pasta. Antes, os caminhos eram relativos ao diretorio
atual e rodar de outro lugar dava "No snapshot provided and couldn't load sample image", que
escondia a causa. A pasta de teste tem acento no nome (cv2.imread falha em silencio com isso no Windows).

Rodar da raiz do projeto:   python tests/test_run_from_any_dir.py
"""
import subprocess
import sys
import tempfile

from _common import ROOT

CODE = f"""
import sys
sys.path.insert(0, {str(ROOT)!r})
from config.room_config import get_swc_poker_config_v3
from poker_table_recognizer import TableAnalyzer
table = TableAnalyzer(get_swc_poker_config_v3()).analyze_table()   # sem imagem: usa a de exemplo da config
assert table.hand == "305616387" and table.pot == 196.0, (table.hand, table.pot)
print("ok")
"""

with tempfile.TemporaryDirectory(prefix="outra_pasta_\u00e7\u00e3_") as elsewhere:
    result = subprocess.run([sys.executable, "-c", CODE], cwd=elsewhere, capture_output=True, text=True)
lines = result.stdout.strip().splitlines()
assert result.returncode == 0 and lines and lines[-1] == "ok", result.stdout[-600:] + result.stderr[-600:]

print("OK: roda de outra pasta (com acento no nome).")
