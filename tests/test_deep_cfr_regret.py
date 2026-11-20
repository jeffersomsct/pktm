"""
Regra de decisao do Deep CFR (pk_agent/experiments/deep_cfr/regret.py), em numpy puro.

O codigo antigo levantava ValueError (probabilidades que nao somam 1 / tamanhos diferentes) no
caso NORMAL de uma rede sem vantagem positiva. Os dois testes "antigo" reproduzem esses crashes.

Rodar da raiz do projeto:   python tests/test_deep_cfr_regret.py
"""
import numpy as np

from _common import ROOT  # noqa: F401  (ajusta sys.path)
from pk_agent.experiments.deep_cfr.regret import masked_softmax, regret_matching

NEG = float("-inf")
legal = [0, 1, 2]

# sem vantagem positiva: uniforme entre as LEGAIS, soma 1, 0 nas ilegais (inclui os -inf do mascaramento)
advantages = np.array([-0.2, -0.1, -0.3, NEG, NEG, NEG, NEG])
strategy = regret_matching(advantages, legal)
assert np.allclose(strategy, [1 / 3, 1 / 3, 1 / 3, 0, 0, 0, 0]) and not np.isnan(strategy).any()
assert np.random.choice(len(strategy), p=strategy) in legal

# com vantagem positiva: proporcional so as positivas
strategy = regret_matching(np.array([2.0, -1.0, 1.0, NEG, NEG, NEG, NEG]), legal)
assert np.allclose(strategy, [2 / 3, 0, 1 / 3, 0, 0, 0, 0])

# acoes legais nao contiguas
strategy = regret_matching(np.array([NEG, 5.0, NEG, NEG, 5.0, NEG, NEG]), [1, 4])
assert np.allclose(strategy, [0, 0.5, 0, 0, 0.5, 0, 0])

# --- o crash do codigo antigo (nao treinada: sem vantagem positiva) ---
old_positive = np.maximum(advantages, 0)
old_strategy = np.ones_like(advantages) / len(advantages)           # uniforme sobre TODAS as 7 acoes
try:
    np.random.choice(len(legal), p=old_strategy[legal])             # soma 3/7, nao 1
except ValueError as error:
    assert "sum to 1" in str(error)
else:
    raise AssertionError("o codigo antigo deveria ter levantado ValueError")

# softmax mascarado: soma 1, 0 nas ilegais, igual ao softmax de referencia, estavel com logits enormes
logits = np.array([1.0, 2.0, 3.0, 9.0, 9.0, 9.0, 9.0])
probabilities = masked_softmax(logits, legal)
reference = np.exp(logits[legal] - logits[legal].max()); reference /= reference.sum()
assert np.allclose(probabilities[legal], reference) and probabilities[3:].sum() == 0 and np.isclose(probabilities.sum(), 1)
huge = masked_softmax(np.array([1000.0, 1001.0, 999.0, 0, 0, 0, 0]), legal)     # exp(1000) estourava (inf/inf = nan)
assert np.isclose(huge.sum(), 1) and not np.isnan(huge).any()

# --- o crash do outro ramo: sortear com len(legais) quando as probabilidades tem o tamanho de todas as acoes ---
try:
    np.random.choice(len(legal), p=probabilities)                   # a de tamanho 3 vs p de tamanho 7
except ValueError as error:
    assert "same size" in str(error)
else:
    raise AssertionError("o codigo antigo deveria ter levantado ValueError")
assert int(np.random.choice(len(probabilities), p=probabilities)) in legal       # como esta agora

print("OK: regret-matching e softmax mascarado; os dois crashes do codigo antigo reproduzidos.")
