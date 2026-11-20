"""
A amostra v3 (torneio) lida contra o que esta ESCRITO na imagem.

Os valores esperados foram conferidos a olho em imagens/table_example.png, nao copiados da saida
do programa. Cobre os bugs corrigidos: vagas lidas como ocupadas, milhar lido como decimal, apostas
fora do ROI, blinds no sentido errado e blinds zeradas.

Rodar da raiz do projeto:   python tests/test_v3_sample.py
"""
from _common import SAMPLE_TITLE, analyze, load_sample, quiet
from poker_table_recognizer import TableAnalyzer

config, image = load_sample()
table = analyze(image)
by_seat = {p.seat: p for p in table.players}

assert table.hand == "305616387", table.hand
assert table.pot == 196.0 and table.small_pot == 56.0, (table.pot, table.small_pot)
assert table.dealer_position == 7, table.dealer_position
assert table.community_cards == [], table.community_cards

# Assentos 1 e 7 estao vazios na imagem (antes todos saiam como presentes).
assert [s for s, p in by_seat.items() if p.is_present] == [0, 2, 3, 4, 5, 6, 8]
assert all(by_seat[s].stack == 0.0 and by_seat[s].current_bet == 0.0 and by_seat[s].name == "" for s in (1, 7))

# (nome, stack, aposta). O assento 2 mostra o rotulo "IGUALAR AP." no lugar do nome: nome nao conferido.
expected = {0: ("jeffpk", 1262, 0), 2: (None, 3033, 40), 3: ("Hosipapa", 6300, 0),
            4: ("SaGiTaRiO25", 1862, 40), 5: ("BlackGaga", 1307, 40), 6: ("Zaebu", 690, 20),
            8: ("Swooppy", 6153, 0)}
for seat, (name, stack, bet) in expected.items():
    player = by_seat[seat]
    assert name is None or player.name == name, (seat, player.name)
    assert player.stack == stack, f"seat {seat}: stack {player.stack}, esperado {stack}"   # 3,033 virava 3.033
    assert player.current_bet == bet, f"seat {seat}: aposta {player.current_bet}, esperado {bet}"

# Blinds: o titulo diz Level 20/40 ante 8; na mesa, 20 no assento 6 (SB) e 40 no 5 (BB). O botao esta no
# assento 7, vazio. A ordem de jogo anda no sentido de indices decrescentes.
assert (table.sb_amount, table.bb_amount, table.ante) == (20.0, 40.0, 8.0)
assert table.bb_positions == [5]
assert by_seat[6].pos_preflop.value == "SB" and by_seat[5].pos_preflop.value == "BB"
assert all(p.pos_preflop is None or p.pos_preflop.value in ("SB", "BB") for p in table.players)   # sem BTN: assento 7 vazio

# Sem titulo nao ha como saber as blinds: ficam zeradas, sem erro.
untitled = analyze(image, title=None)
assert (untitled.sb_amount, untitled.bb_amount, untitled.ante) == (0.0, 0.0, 0.0)

# Captura com outro tamanho: os ROIs sao pixel-exatos, entao deve avisar (uma vez) em vez de calar.
import contextlib, io  # noqa: E402
buffer = io.StringIO()
analyzer = TableAnalyzer(config)
with contextlib.redirect_stdout(buffer):
    analyzer.analyze_table(image[:, :-14])
    analyzer.analyze_table(image[:, :-14])
assert buffer.getvalue().count("AVISO") == 1, buffer.getvalue()

print("OK: amostra v3 confere com a imagem (presenca, stacks, apostas, blinds, dealer).")
