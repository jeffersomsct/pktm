"""
core/printer.py
Impressao formatada do estado da mesa.

Migracao da versao anterior:
  - p.position -> p.seat
  - community_cards: List[tuple] -> List[Card] (usar card.rank / card.suit)
  - pot / small_pot: str -> float (formatar com :.2f)
  - Novas colunas: Is Hero, All-In (no lugar de Pending BB duplicado)
"""
from colorama import Fore, Style, init

init(autoreset=False, strip=False, convert=True)


def _fmt_chip(v) -> str:
    """
    Formata um valor em chips (mBTC/SwC) com ate 3 casas decimais,
    sem zeros a direita. Exemplos:
        3.033   -> '3.033'
        6.153   -> '6.153'
        1262.0  -> '1262'
        0.1     -> '0.1'
        0.0     -> '0'
    SwC usa mBTC com 3 casas; .2f cortava o 3o digito que o OCR captura.
    """
    if v is None or v == "":
        return "0"
    try:
        s = f"{float(v):.3f}".rstrip("0").rstrip(".")
        return s if s else "0"
    except (TypeError, ValueError):
        return str(v)


def print_players_table(room):
    """
    Imprime a tabela de jogadores formatada.
    """
    players = room.players
    header    = "+--------------+----------+---------+----------------+------------------+-----------+----------+------------+------------+--------+"
    title     = "| Nome         | Seat     |  Stack  |   Aposta Atual | Posicao Pre-flop | Is Present| Is Active| Just Joined| Pending BB | IsHero |"
    separator = "+==============+==========+=========+================+==================+===========+==========+============+============+========+"

    print(f"\n{Fore.CYAN}{header}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{title}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{separator}{Style.RESET_ALL}")

    for p in players:
        name_color = Fore.GREEN if p.is_present else Fore.RED
        present_color = Fore.GREEN if p.is_present else Fore.RED
        active_color = Fore.GREEN if p.is_active else Fore.RED
        hero_color = Fore.YELLOW if p.is_hero else Fore.WHITE

        nome       = f"{name_color}{p.name:<12}{Style.RESET_ALL}"
        seat       = f"{p.seat:>8}"
        stack      = f"{_fmt_chip(p.stack):>7}"
        aposta     = f"{_fmt_chip(p.current_bet):>14}"

        if p.pos_preflop and hasattr(p.pos_preflop, "value"):
            pos_str = str(p.pos_preflop.value)
        elif p.pos_preflop:
            pos_str = str(p.pos_preflop)
        else:
            pos_str = "N/A"
        pos_preflop = f"{pos_str:<16}"

        is_present = f"{present_color}{str(p.is_present):<9}{Style.RESET_ALL}"
        is_active  = f"{active_color}{str(p.is_active):<8}{Style.RESET_ALL}"
        just_joined = f"{str(p.just_joined):<10}"
        pending_bb = f"{str(p.pending_big_blind):<10}"
        is_hero    = f"{hero_color}{str(p.is_hero):<6}{Style.RESET_ALL}"

        linha = (f"| {nome} | {seat} | {stack} | {aposta} | {pos_preflop} "
                 f"| {is_present} | {is_active} | {just_joined} | "
                 f"{pending_bb} | {is_hero} |")
        print(linha)

    print(f"{Fore.CYAN}{separator}{Style.RESET_ALL}")


def print_table_status(room):
    """
    Imprime o status da mesa formatado com cartas comunitarias.
    """
    dealer_pos = room.dealer_position
    pot = room.pot
    small_pot = room.small_pot
    hand = room.hand_id
    community_cards = room.community_cards or []

    suit_symbols = {
        'H': f"{Fore.RED}♥{Fore.WHITE}",
        'D': f"{Fore.RED}♦{Fore.WHITE}",
        'S': f"{Fore.WHITE}♠{Fore.WHITE}",
        'C': f"{Fore.WHITE}♣{Fore.WHITE}",
    }

    if community_cards:
        cards_formatted = []
        for card in community_cards:
            # card eh Card dataclass (rank, suit), nao tuple
            rank = getattr(card, "rank", None) or (card[0] if isinstance(card, tuple) else "?")
            suit = getattr(card, "suit", None) or (card[1] if isinstance(card, tuple) else "?")
            if rank and suit:
                suit_symbol = suit_symbols.get(suit, suit)
                cards_formatted.append(f"{Fore.WHITE}{rank}{suit_symbol}")
            else:
                cards_formatted.append("??")
        cards_str = ' '.join(cards_formatted)
    else:
        cards_str = 'Nenhuma'

    pot_str = f"${_fmt_chip(pot)}" if isinstance(pot, (int, float)) else str(pot)
    small_pot_str = (f"${_fmt_chip(small_pot)}" if small_pot else "N/A") if isinstance(small_pot, (int, float)) else (small_pot or "N/A")

    print(f"\n{Fore.YELLOW}╔═══════════════════════════════════════════════════════════════════════════════════════════╗")
    print(f"║{Fore.WHITE} {'Hand:'}{Fore.GREEN} {hand}{Fore.CYAN}            🎲 MESA DE POKER - STATUS ATUAL                                {Fore.YELLOW}║")
    print(f"╠═══════════════════════════════════════════════════════════════════════════════════════════╣")
    print(f"║ {Fore.WHITE}Dealer: Seat {Fore.GREEN}{dealer_pos}{Fore.WHITE} {'🃏'*3}  |  Pote: {Fore.GREEN}{pot_str}{Fore.WHITE} {'💰'*1}    |    Small Pot: {Fore.YELLOW}{small_pot_str}{Fore.YELLOW}                       ║")
    print(f"║ {Fore.WHITE}Cartas na Mesa: {cards_str}{' '*max(0, 50-len(cards_str))}{Fore.YELLOW}                                                               ║")
    print(f"╚═══════════════════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")


def print_hand_summary(hand):
    """
    Novo: imprime resumo do HandRecord (sequencia de acoes por street).
    """
    if not hand:
        print("Sem HandRecord para exibir.")
        return

    print(f"\n=== HAND {hand.hand_id} (table: {hand.table_id}) ===")
    print(f"  Blinds: SB={hand.sb_amount} BB={hand.bb_amount} Ante={hand.ante}")
    print(f"  Dealer seat: {hand.dealer_seat}")
    if hand.hero_seat is not None:
        hero_cards_str = " ".join(str(c) for c in hand.hero_cards) or "(nao capturadas)"
        print(f"  Hero: seat {hand.hero_seat}  cards: {hero_cards_str}")

    from core.models import Street
    for street in [Street.PREFLOP, Street.FLOP, Street.TURN, Street.RIVER]:
        sr = hand.streets.get(street)
        if not sr:
            continue
        board_str = " ".join(str(c) for c in sr.board_before) or "(vazio)"
        print(f"  [{street.value}] board_before={board_str}  "
              f"pot {_fmt_chip(sr.pot_before)} -> {_fmt_chip(sr.pot_after)}  "
              f"acoes: {len(sr.actions)}")
        for a in sr.actions:
            amt = f" {_fmt_chip(a.amount)}" if a.amount > 0 else ""
            print(f"      #{a.order:02d} {a.player_name:<14} {a.type.value}{amt}")

    if hand.winners:
        print(f"  Vencedores: {', '.join(hand.winners)}")
