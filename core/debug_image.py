import numpy as np
import cv2
from typing import List

def create_debug_image(image: np.ndarray, config, dealer_position: int, players: list, community_cards: List[tuple] = None, player_positions: dict = None):
    debug_image = image.copy()
    roi_config = config.roi_config
    
    # Mapeamento de naipes para emojis
    suit_emojis = {
        'S': '♠',  # Espadas
        'H': '♥',  # Copas
        'D': '♦',  # Ouros
        'C': '♣'   # Paus
    }

    # Desenha as ROIs e cartas da comunidade
    if hasattr(roi_config, 'ranks') and hasattr(roi_config, 'suits'):
        for i in range(1, 6):  # Para cada posição de carta (flop, turn, river)
            rank_roi = getattr(roi_config.ranks, f'rank_{i}', None)
            suit_roi = getattr(roi_config.suits, f'suit_{i}', None)
            
            # Verifica se temos uma carta reconhecida para esta posição
            card_text = ''
            card_info = ''
            if community_cards and i <= len(community_cards):
                rank, suit = community_cards[i-1]
                card_text = f"{rank}{suit_emojis.get(suit, suit)}"
                card_info = f"Card {i}: {rank}{suit}"
            
            # Desenha ROI do rank
            if rank_roi:
                x, y, w, h = rank_roi
                # Desenha retângulo laranja para o rank
                cv2.rectangle(debug_image, (x, y), (x+w, y+h), (0, 165, 255), 2)
                
                # Se tiver carta reconhecida, exibe o texto
                if card_text:
                    # Fundo para o texto
                    (text_w, text_h), _ = cv2.getTextSize(card_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                    cv2.rectangle(debug_image, (x, y - text_h - 10), 
                                (x + text_w + 10, y), (0, 0, 0), -1)
                    # Texto da carta
                    cv2.putText(debug_image, card_text, (x + 5, y - 5), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # Desenha ROI do naipe
            if suit_roi:
                x, y, w, h = suit_roi
                # Desenha retângulo roxo para o naipe
                cv2.rectangle(debug_image, (x, y), (x+w, y+h), (255, 0, 255), 2)
                
                # Se tiver carta reconhecida, exibe o naipe
                if card_text and len(card_text) > 1:
                    suit = card_text[-1]  # Pega o emoji do naipe
                    (text_w, text_h), _ = cv2.getTextSize(suit, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                    cv2.rectangle(debug_image, (x, y - text_h - 10), 
                                (x + text_w + 10, y), (0, 0, 0), -1)
                    cv2.putText(debug_image, suit, (x + 5, y - 5), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            # Exibe o texto da carta no canto da imagem
            if card_info:
                cv2.putText(debug_image, card_info, 
                          (10, 30 + (i-1)*25), cv2.FONT_HERSHEY_SIMPLEX, 
                          0.7, (0, 255, 255), 2)

    # Draw ROIs for stacks
    for name, (x, y, w, h) in config.roi_config.stacks.items():
        cv2.rectangle(debug_image, (x, y), (x+w, y+h), (0, 255, 0), 1)
        position = int(name.split('_')[1])
        stack_value = players[position].stack if position < len(players) else 0
        cv2.putText(debug_image, f"Stack: {stack_value}", (x, y+h+15), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Draw ROIs for bets
    for name, (x, y, w, h) in config.roi_config.bets.items():
        cv2.rectangle(debug_image, (x, y), (x+w, y+h), (255, 0, 0), 1)
        position = int(name.split('_')[1])
        bet_value = players[position].current_bet if position < len(players) else 0
        cv2.putText(debug_image, f"Bet: {bet_value}", (x, y-5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    # Draw ROIs for names
    for name, (x, y, w, h) in config.roi_config.names.items():
        # Desenha o retângulo ao redor da área do nome
        cv2.rectangle(debug_image, (x, y), (x+w, y+h), (0, 0, 255), 1)
        
        position = int(name.split('_')[1])
        player_name = players[position].name if position < len(players) else ""
        
        # Get position information if available
        position_text = ""
        if player_positions and player_name in player_positions:
            pos_info = player_positions[player_name]
            position_text = pos_info.position_name.value

        # Configurações de texto melhoradas
        text = f"{player_name}"
        font = cv2.FONT_HERSHEY_DUPLEX  # Fonte mais limpa e moderna
        font_scale = 0.6
        thickness = 1
        text_color = (200, 255, 200)  # Verde claro suave (BGR)
        bg_color = (40, 40, 40)      # Cinza escuro para fundo

        # Draw position text above name if available
        if position_text:
            # Position text settings
            pos_font_scale = 0.5
            pos_thickness = 1
            pos_color = (255, 200, 100)  # Laranja suave para posições
            pos_bg_color = (60, 40, 20)   # Marrom escuro para fundo da posição
            
            # Calculate position text size
            (pos_text_width, pos_text_height), _ = cv2.getTextSize(
                position_text, font, pos_font_scale, pos_thickness
            )
            
            # Position text coordinates (above the name background)
            pos_bg_x1 = x
            pos_bg_y1 = y - text_height - 10 - pos_text_height - 8  # Above name background
            pos_bg_x2 = x + pos_text_width
            pos_bg_y2 = y - text_height - 12  # Just above name background
            
            # Draw position background
            cv2.rectangle(
                debug_image,
                (pos_bg_x1, pos_bg_y1),
                (pos_bg_x2, pos_bg_y2),
                pos_bg_color,
                -1  # Preenchido
            )
            
            # Draw position text
            cv2.putText(
                debug_image,
                position_text,
                (x, y - text_height - 15),
                font,
                pos_font_scale,
                pos_color,
                pos_thickness,
                lineType=cv2.LINE_AA
            )

        # Calcula o tamanho do texto para criar o fundo
        (text_width, text_height), baseline = cv2.getTextSize(
            text, font, font_scale, thickness
        )

        # Define as coordenadas do retângulo de fundo (adjusted for position text)
        bg_x1 = x
        bg_y1 = y - text_height - 10  # 10px acima do topo do retângulo
        bg_x2 = x + text_width
        bg_y2 = y - 5
        
        # Desenha o retângulo de fundo
        cv2.rectangle(
            debug_image, 
            (bg_x1, bg_y1), 
            (bg_x2, bg_y2), 
            bg_color, 
            -1  # Preenchido
        )
        
        # Desenha o texto sobre o fundo
        cv2.putText(
            debug_image, 
            text, 
            (x, y - 8),  # Posição ajustada
            font,
            font_scale,
            text_color,
            thickness,
            lineType=cv2.LINE_AA  # Anti-aliasing para melhor suavização
        )

    # Draw ROI for pot
    for name, (x, y, w, h) in config.roi_config.pot.items():
        cv2.rectangle(debug_image, (x, y), (x+w, y+h), (255, 255, 0), 1)
        cv2.putText(debug_image, f"Pot", (x, y-5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
    # Draw ROI for Hand Id
    for name, (x, y, w, h) in config.roi_config.hand.items():
        cv2.rectangle(debug_image, (x, y), (x+w, y+h), (255, 255, 150), 1)
        cv2.putText(debug_image, f"Hand", (x, y-5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

    # Draw ROI for small pot
    for name, (x, y, w, h) in config.roi_config.smallpot.items():
        cv2.rectangle(debug_image, (x, y), (x+w, y+h), (0, 255, 255), 1)
        cv2.putText(debug_image, f"Small Pot", (x, y-5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

    # Mark dealer position if detected
    if dealer_position != -1 and dealer_position in config.dealer_config.positions:
        x, y = config.dealer_config.positions[dealer_position]
        cv2.circle(debug_image, (x, y), 3, (0, 100, 255), -1)
        cv2.putText(debug_image, f"Dealer {dealer_position}", (x+10, y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    
    # Mark SB and BB positions
    for player in players:
        pos_label = ''
        if player.pos_preflop:
            pos_label = player.pos_preflop.value  # Extrai o valor string: 'SB' ou 'BB'

        if pos_label in ['SB', 'BB']:
            # Assumindo que as posições estão mapeadas como chaves em self.config.dealer_config.positions
            if player.position in config.dealer_config.positions:
                x, y = config.dealer_config.positions[player.position]
                color = (0, 255, 255) if pos_label == 'SB' else (150, 200, 0)  # Amarelo para SB, Azul para BB
                cv2.circle(debug_image, (x, y), 5, color, -1)
                cv2.putText(debug_image, f"{pos_label}", (x + 10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # Draw community cards ROIs
    if hasattr(roi_config, 'ranks') and hasattr(roi_config, 'suits'):
    
        # Draw rank ROI
        x, y, w, h = roi_config.ranks[f"rank"]
        cv2.rectangle(debug_image, (x, y), (x+w, y+h), (0, 255, 0), 1)
        cv2.putText(debug_image, f"rank", (x, y-5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Draw suit ROI
        x, y, w, h = roi_config.suits[f"suit"]
        cv2.rectangle(debug_image, (x, y), (x+w, y+h), (255, 0, 0), 1)
        cv2.putText(debug_image, f"suit", (x, y-5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    # Save debug image
    print("Debug Mode ON: Image save: debug_table_recognition.png" )
    cv2.imwrite("debug_table_recognition.png", debug_image)