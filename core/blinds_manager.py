from codemap import Position

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


    def id_positions(self, players):    
        """
        Identifica as posições:

        UTG = "UTG"       # Under The Gun
        MP = "MP"         # Middle Position
        CO = "CO"         # Cutoff
        HJ = "HJ"         # Hijack (just before the cutoff)
        LJ = "LJ"         # Lojack (just before hijack)
        EP = "EP"         # Early Position (can represent UTG+1)
        OTB = "OTB"       # Out of position (any position when you’re not in the last positions)
    
        """
        for p in players:
            if p.is_present and p.stack > 0:
                active_count += 1
                if p.current_bet > 0:
                    if bb_player == -1:
                        bb_player = p
                    elif sb_player == -1:
                        sb_player = p
        dealer_position = players.position
        ordened_players = players[dealer_position+1:] + players[:dealer_position+1]

    
        if active_count > 3 and bb_player != -1:
            bb_idx = ordered_players.index(bb_player)
            positions = [Position.UTG, Position.MP, Position.CO]
            pos_idx = 0
            
            # Assign positions after BB
            for player in ordered_players[bb_idx+1:] + ordered_players[:bb_idx]:
                if player.is_present and player.stack > 0:
                    if player != sb_player and player != bb_player and pos_idx < len(positions):
                        for p in players:
                            if p.position == player.position:
                                p.pos_preflop = positions[pos_idx]
                                pos_idx += 1
                                break
        
        return sb_player, bb_player
    
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
    
    def _next_position(self, current_position):
        """Calcula próxima posição na mesa"""
        return (current_position + 1) % 10  # Assumindo mesa de 10 lugares
    

    # Inicialização
#blinds_manager = BlindsManager(min_small_blind=1, min_big_blind=2)
# # Identificar blinds
#sb_info, bb_info = BlindsManager.identify_blinds(players, dealer_position)

# # Verificar apostas iguais ao BB no pré-flop
# bb_positions = BlindsManager.validate_preflop_bets(players, bb_amount=2)
