from rooms.poker_room import PokerRoom
from core.window_handler import detect_window
from core.printer import print_players_table, print_table_status
from action.poker_hand_state import PokerHandState
from core.debug_image import create_debug_image


def main():
    # Configuração
    pkr_room_name = "SwC Poker - Logged in as jeffpk"
    live = False  # True para captura ao vivo, False para usar imagem de exemplo
    
    # Criar instância da sala
    room = PokerRoom(pkr_room_name)
    
    # Capturar snapshot da mesa
    snapshot = detect_window(pkr_room_name) if live else None
    
    # Atualizar estado da mesa
    room.update_table_state(snapshot)
    
    # Criar estado da mão
    hand_state = PokerHandState(
        hand_id=room.hand_id,
        num_players=len(room.players),
        dealer_position=room.dealer_position
    )
    
    # Atualizar cartas comunitárias (determina a rodada)
    hand_state.update_community_cards(room.community_cards)
    
    # Calcular posições de todos os jogadores
    hand_state.calculate_positions(room.players)

    # Create debug image with positions if debug mode is enabled and snapshot is available
    if snapshot is not None:
        create_debug_image(
            snapshot, 
            room.config, 
            room.dealer_position, 
            room.players, 
            room.community_cards,
            hand_state.player_positions
        )
    
    # Atualizar pot
    hand_state.pot = float(room.pot)
    
    # Exibir informações
    print_table_status(room)
    print_players_table(room)
    print("\n=== ESTADO DA MÃO ===")
    print(f"Hand ID: {hand_state.hand_id}")
    print(f"Rodada: {hand_state.current_street.value}")
    print(f"Cartas do board: {hand_state.community_cards}")
    print(f"Pot: ${hand_state.pot}")
    print("\n=== POSIÇÕES ===")
    for name, pos_info in hand_state.player_positions.items():
        btn = "[BTN]" if pos_info.is_button else ""
        print(f"{name:20} {pos_info.position_name.value:8} {btn}")


if __name__ == "__main__":
    main()


