from colorama import Fore, Style, init

# Inicializa colorama (necessário para Windows)
init(autoreset=False, strip=False, convert=True)

def print_players_table(room):
    """
    Imprime a tabela de jogadores formatada.
    
    Args:
        room: Instância do PokerRoom com todas as informações da mesa
    """
    players = room.players
    
    header =    f"+--------------+----------+---------+----------------+------------------+-----------+----------+------------+------------+"
    title =     f"| Nome         | Posição  |  Stack  |   Aposta Atual | Posição Pré-flop | Is Present| Is Active| Just Joined| Pending BB |"
    separator = f"+==============+==========+=========+================+==================+===========+==========+============+============+"
    
    print(f"\n{Fore.CYAN}{header}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{title}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{separator}{Style.RESET_ALL}")
    
    for p in players:
        name_color = Fore.GREEN if p.is_present else Fore.RED
        present_color = Fore.GREEN if p.is_present else Fore.RED
        active_color = Fore.GREEN if p.is_active else Fore.RED
        
        # Ajustando as larguras para bater com o cabeçalho
        nome = f"{name_color}{p.name:<12}{Style.RESET_ALL}"        
        posicao = f"{p.position:>8}"                                
        stack = f"{p.stack:>7.2f}"                               
        aposta = f"{p.current_bet:>14.2f}"
        # Converte pos_preflop para string se for um enum
        pos_str = str(p.pos_preflop.value) if p.pos_preflop and hasattr(p.pos_preflop, 'value') else (str(p.pos_preflop) if p.pos_preflop else 'N/A')
        pos_preflop = f"{pos_str:<16}"            
        is_present = f"{present_color}{str(p.is_present):<9}{Style.RESET_ALL}"  
        is_active = f"{active_color}{str(p.is_active):<8}{Style.RESET_ALL}"    
        just_joined = f"{str(p.just_joined):<10}"                
        pending_bb = f"{str(p.pending_big_blind):<10}"           
        
        linha = f"| {nome} | {posicao} | {stack} | {aposta} | {pos_preflop} | {is_present} | {is_active} | {just_joined} | {pending_bb} |"
        print(linha)
    
    print(f"{Fore.CYAN}{separator}{Style.RESET_ALL}")

def print_table_status(room):
    """
    Imprime o status da mesa formatado com cartas comunitárias.
    
    Args:
        room: Instância do PokerRoom com todas as informações da mesa
    """
    # Informações gerais da mesa (diretamente do room)
    dealer_pos = room.dealer_position
    pot = room.pot
    small_pot = room.small_pot
    hand = room.hand_id
    community_cards = room.community_cards or []

    # Mapeamento de naipes para símbolos coloridos
    suit_symbols = {
        'H': f"{Fore.RED}♥{Fore.WHITE}",    # Copas em vermelho
        'D': f"{Fore.RED}♦{Fore.WHITE}",    # Ouros em vermelho
        'S': f"{Fore.WHITE}♠{Fore.WHITE}",  # Espadas em branco
        'C': f"{Fore.WHITE}♣{Fore.WHITE}"   # Paus em branco
    }

    # Format community cards string
    if community_cards:
        cards_formatted = []
        for rank, suit in community_cards:
            if rank and suit:
                suit_symbol = suit_symbols.get(suit, suit)
                cards_formatted.append(f"{Fore.WHITE}{rank}{suit_symbol}")
            else:
                cards_formatted.append("??")
        cards_str = ' '.join(cards_formatted) if cards_formatted else 'Nenhuma'
    else:
        cards_str = 'Nenhuma'
    
    print(f"\n{Fore.YELLOW}╔═══════════════════════════════════════════════════════════════════════════════════════════╗")
    print(f"║{Fore.WHITE} {'Hand:'}{Fore.GREEN} {hand}{Fore.CYAN}            🎲 MESA DE POKER - STATUS ATUAL                                {Fore.YELLOW}║")
    print(f"╠═══════════════════════════════════════════════════════════════════════════════════════════╣")
    print(f"║ {Fore.WHITE}Dealer: Posição {Fore.GREEN}{dealer_pos}{Fore.WHITE} {'🃏'*3}  |  Pote: {Fore.GREEN}${pot}{Fore.WHITE} {'💰'*1}    |    Small Pot: {Fore.YELLOW}{small_pot if small_pot else 'N/A'}{Fore.YELLOW}                       ║")
    print(f"║ {Fore.WHITE}Cartas na Mesa: {cards_str}{' '*max(0, 50-len(cards_str))}{Fore.YELLOW}                                                               ║")
    print(f"╚═══════════════════════════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
