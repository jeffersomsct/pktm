"""
Posicoes BTN / SB / BB a partir do dealer. A ordem de jogo na SwC anda em indices DECRESCENTES
(assentos numerados no sentido anti-horario da tela, acao no horario). O codigo antigo andava no
sentido crescente e dava SB e BB errados.

Os casos de mesa real foram conferidos a olho em imagens reais (fichas de SB/BB na frente de cada um).

Rodar da raiz do projeto:   python tests/test_blinds.py
"""
from _common import ROOT  # noqa: F401  (ajusta sys.path)
from core.blinds import assign_blinds
from core.models import Player, Position


def seat_positions(present, dealer, n_seats=9, step=-1):
    players = [Player(name="", seat=s, stack=1.0, current_bet=0.0, is_present=s in present, is_active=s in present)
               for s in range(n_seats)]
    bb = assign_blinds(players, dealer, n_seats, step)
    return {p.seat: p.pos_preflop.value for p in players if p.pos_preflop}, bb


# Mesa real 1 (table_example.png): botao no assento 7, VAZIO. Fichas: 20 no assento 6, 40 no 5.
assert seat_positions({0, 2, 3, 4, 5, 6, 8}, dealer=7) == ({6: "SB", 5: "BB"}, [5])
# Mesa real 2 (gravacao, mao 305617192): botao no 5, fichas 40 no assento 4 e 80 no 3.
assert seat_positions({0, 2, 3, 4, 5, 6, 7, 8}, dealer=5) == ({5: "BTN", 4: "SB", 3: "BB"}, [3])
# Mesa real 3 (gravacao, mao 305617200): botao no 4, fichas 40 no assento 3 e 80 no 2.
assert seat_positions({0, 2, 3, 4, 5, 6, 7, 8}, dealer=4) == ({4: "BTN", 3: "SB", 2: "BB"}, [2])

# Volta ao redor da mesa (o dealer no assento 0 faz o SB cair no 8).
assert seat_positions({0, 1, 2}, dealer=0, step=-1) == ({0: "BTN", 2: "SB", 1: "BB"}, [1])
assert seat_positions({0, 8, 5}, dealer=0) == ({0: "BTN", 8: "SB", 5: "BB"}, [5])

# Heads-up: o dealer e o SB e o outro e o BB.
assert seat_positions({0, 3}, dealer=0) == ({0: "SB", 3: "BB"}, [3])
assert seat_positions({0, 3}, dealer=3) == ({3: "SB", 0: "BB"}, [0])
# Heads-up com o botao em assento vazio: vale a regra geral.
assert seat_positions({0, 3}, dealer=7) == ({3: "SB", 0: "BB"}, [0])

# Sem dealer detectado ou sem jogadores suficientes: nada e marcado.
assert seat_positions({0, 2, 3}, dealer=-1) == ({}, [])
assert seat_positions({4}, dealer=4) == ({}, [])
assert seat_positions(set(), dealer=2) == ({}, [])

# Sentido +1 (outra sala, se um dia): inverte a ordem.
assert seat_positions({0, 2, 3, 4}, dealer=2, step=1) == ({2: "BTN", 3: "SB", 4: "BB"}, [4])

assert Position.SB.value == "SB" and Position.BB.value == "BB" and Position.BTN.value == "BTN"
print("OK: posicoes de blinds (mesas reais, heads-up, volta, dealer ausente).")
