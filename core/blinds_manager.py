from action.poker_hand_state import Position

class BlindsManager:
    def __init__(self, min_small_blind=1, min_big_blind=2):
        """
        """
        self.min_small_blind = min_small_blind
        self.min_big_blind = min_big_blind
        
    def identify_blinds(self, players, dealer_position):
        """
        Identifica SmallBlind e BigBlind considerando casos especiais
        """
        players[dealer_position].pos_preflop = Position.BTN

        if not players or len(players) < 2:
            return None, None
        # Ordena os Jogadores pelo Dealer
        ordened_players = players[dealer_position+1:] + players[:dealer_position+1]
        ordened_players = ordened_players[::-1]
        
       
        sb_player = -1
        bb_player = -1
        
        # Find BB first (first player with bet)
        for player in ordened_players[1:]:
            if player.current_bet > 0 and sb_player == -1:
                sb_player = player
                # Update BB position
                for p in players:
                    if p.position == player.position:
                        p.pos_preflop = Position.SB
                        break
                continue
            if sb_player != -1 and player.current_bet > 0:
                bb_player = player
                # Update BB position
                for p in players:
                    if p.position == player.position:
                        p.pos_preflop = Position.BB
                        break
                break
        
        return players


    def validate_preflop_bets(self, players, bb_amount):
        """
        Valida apostas do pré-flop, identificando apostas iguais ao BB
        de jogadores que acabaram de entrar na mesa
        
        Args:
            players: Lista de jogadores
            bb_amount: Valor do BigBlind
        
        Returns:
            list: Lista de posições com apostas iguais ao BB
        """
        bb_positions = []
        
        for player in players:
            if not player.is_present:
                continue
                
            if (player.current_bet == bb_amount and 
                player.just_joined and 
                player.stack > 0):
                bb_positions.append(player.position)
            print("current bet: ",player.current_bet, "joined: ", player.just_joined, "Stack:", player.stack, "Position: ", player.position)
                
        return bb_positions
    

    # Inicialização
#blinds_manager = BlindsManager(min_small_blind=1, min_big_blind=2)
# # Identificar blinds
#sb_info, bb_info = BlindsManager.identify_blinds(players, dealer_position)

# # Verificar apostas iguais ao BB no pré-flop
# bb_positions = BlindsManager.validate_preflop_bets(players, bb_amount=2)
