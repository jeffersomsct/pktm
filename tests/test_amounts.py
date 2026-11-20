"""
Valores numericos: separador de milhar lido como '.', decimais de centavos e blinds do titulo.

Rodar da raiz do projeto:   python tests/test_amounts.py
"""
from _common import ROOT
from core.blinds import parse_blinds
from poker_table_recognizer import CharacterRecognizer

recognizer = CharacterRecognizer(ROOT / "imgs" / "models" / "swc" / "v3")

# O OCR le a virgula de milhar como ponto: "6,153" chega como "6.153".
amounts = {
    "6.153": 6153.0, "3.033": 3033.0, "1.862": 1862.0,          # os tres casos reais da amostra
    "1.234.567": 1234567.0, "100.000": 100000.0,
    "6.153.50": 6153.5, "1.234.56": 1234.56,                    # milhar + centavos
    "1.60": 1.6, "12.92": 12.92, "0.04": 0.04, "0.125": 0.125,  # decimais de verdade ficam decimais
    "10.5": 10.5, "196": 196.0, "690": 690.0,
    "1,262": 1262.0, "6,153.50": 6153.5,                        # virgula que chegou como virgula
    "": 0.0, "abc": 0.0, "1.5.2": 0.0, ".": 0.0,                # lixo nunca levanta excecao
}
for text, expected in amounts.items():
    got = recognizer.convert_to_float(text)
    assert got == expected, f"convert_to_float({text!r}) = {got}, esperado {expected}"

titles = {
    # torneio: vale o nivel ATUAL (o primeiro), nao o "Next Level"
    "Hourly Freeroll - NLH [10 Chips]  -  Level 20/40 ante 8;  Next Level 25/50 ante 10": (20.0, 40.0, 8.0),
    "Hourly Freeroll - NLH [10 Chips]  -  Level 40/80 ante 16;  Next Level 50/100 ante 20": (40.0, 80.0, 16.0),
    "Level 100/200;  Next Level 150/300": (100.0, 200.0, 0.0),
    # cash
    "NL Hold'em 0.02/0.04 - Mesa": (0.02, 0.04, 0.0),
    "": (0.0, 0.0, 0.0), None: (0.0, 0.0, 0.0), "SwC Poker - Logged in as x": (0.0, 0.0, 0.0),
}
for title, expected in titles.items():
    got = parse_blinds(title)
    assert got == expected, f"parse_blinds({title!r}) = {got}, esperado {expected}"

print(f"OK: {len(amounts)} valores e {len(titles)} titulos.")
