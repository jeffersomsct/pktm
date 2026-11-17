"""
config/templates.py
Descobre os templates de uma categoria lendo a PASTA, sem mapeamento manual.

Convencao dos nomes de arquivo (a mesma que as pastas ja seguem):

    A.png, Av2.png      -> 'A'   sufixo vN = variante do mesmo caractere
    a_.png, a_v2.png    -> 'a'   minuscula leva '_' (o Windows nao distingue a.png de A.png)
    ponto.png           -> '.'
    virgula.png         -> ','
    barra.png           -> '/'
    nada.png            -> ''    (area em branco)
    10.png              -> 'T'   dez, como o resto do projeto escreve
    _.png, _v2.png      -> '_'

Para DESATIVAR um template sem apagar o arquivo, mova-o para uma subpasta
`_off/` dentro da categoria (so *.png direto na pasta sao lidos).
"""
import re
from pathlib import Path
from typing import Dict, List, Optional

_SYMBOLS = {"ponto": ".", "virgula": ",", "barra": "/", "nada": "", "10": "T"}
_VARIANT = re.compile(r"_?v\d+$")          # ...v2, ..._v2, ...v10


def char_from_filename(stem: str) -> Optional[str]:
    """Caractere representado por um template, ou None se o nome nao segue a convencao."""
    if re.fullmatch(r"_(v\d+)?", stem):     # o proprio caractere '_'
        return "_"
    base = _VARIANT.sub("", stem)
    if base in _SYMBOLS:
        return _SYMBOLS[base]
    if len(base) == 2 and base[1] == "_":   # a_ -> a
        return base[0]
    if len(base) == 1:
        return base
    return None


def discover_templates(directory: Path) -> Dict[str, List[Path]]:
    """{caractere: [arquivos .png]} para todos os templates da pasta."""
    found: Dict[str, List[Path]] = {}
    for path in sorted(Path(directory).glob("*.png")):
        char = char_from_filename(path.stem)
        if char is None:
            print(f"Template ignorado (nome fora da convencao): {path}")
            continue
        found.setdefault(char, []).append(path)
    return found
