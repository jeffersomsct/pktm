"""
O v3 nao depende de v1/v2: dá para apagar imgs/models/swc/v1 e v2 sem quebrar nada.

Rodar da raiz do projeto:   python tests/test_v3_self_contained.py
"""
import re

from _common import ROOT, load_sample
from poker_table_recognizer import RecognitionCategory

# 1) nenhum arquivo .py aponta para as pastas v1/v2 dos templates
pattern = re.compile(r"swc[/\\]v[12]\b")
offenders = []
for path in ROOT.rglob("*.py"):
    if ".git" in path.parts or path.name == "test_v3_self_contained.py":
        continue
    if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
        offenders.append(str(path.relative_to(ROOT)))
assert not offenders, f"referencias a v1/v2 em: {offenders}"

# 2) tudo o que a config v3 usa existe DENTRO de imgs/models/swc/v3
config, _ = load_sample()
base = ROOT / config.template_path
assert base.parts[-3:] == ("models", "swc", "v3"), base
for category in RecognitionCategory:
    folder = base / category.value
    assert folder.is_dir() and any(folder.glob("*.png")), f"faltam templates em {folder}"
assert (ROOT / config.sample_image_path).is_file()

# 3) os glifos trazidos do v1 estao no v3 (aposta com 7 e nome com 9)
assert (base / "bet" / "7.png").is_file() and (base / "names" / "9.png").is_file()

print("OK: o v3 e autocontido (pode apagar v1 e v2).")
