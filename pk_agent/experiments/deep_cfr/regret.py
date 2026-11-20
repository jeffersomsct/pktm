"""
pk_agent/experiments/deep_cfr/regret.py
A regra de decisao do Deep CFR, em numpy puro (o resto do pacote depende de torch).
"""
from typing import Sequence

import numpy as np


def regret_matching(advantages: np.ndarray, legal_actions: Sequence[int]) -> np.ndarray:
    """
    Estrategia por regret-matching sobre as acoes LEGAIS.

    Devolve um vetor do tamanho de `advantages`, com probabilidade 0 nas acoes ilegais e soma 1.
    Sem vantagem positiva, a estrategia e uniforme entre as acoes legais. (A versao antiga fazia o
    uniforme sobre TODAS as acoes; ao fatiar so as legais a soma ficava < 1 e o np.random.choice
    levantava "probabilities do not sum to 1" quase sempre, ja que uma rede nao treinada raramente
    tem vantagem positiva.)
    """
    legal = list(legal_actions)
    strategy = np.zeros(len(advantages))
    positive = np.maximum(np.asarray(advantages, dtype=float)[legal], 0.0)
    total = positive.sum()
    strategy[legal] = positive / total if total > 0 else 1.0 / len(legal)
    return strategy


def masked_softmax(logits: np.ndarray, legal_actions: Sequence[int]) -> np.ndarray:
    """Softmax so entre as acoes legais (0 nas ilegais), estavel para logits grandes."""
    legal = list(legal_actions)
    probabilities = np.zeros(len(logits))
    shifted = np.asarray(logits, dtype=float)[legal]
    shifted = np.exp(shifted - shifted.max())
    probabilities[legal] = shifted / shifted.sum()
    return probabilities
