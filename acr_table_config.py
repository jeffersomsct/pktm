# acr_config.py

class ACRTableConfig:
    """
    Contém coordenadas aproximadas de cada ROI na mesa de pôquer da ACR.
    Ajuste de acordo com sua tela/resolução.
    """
    # Exemplo para 6 ou 9 jogadores (adapte à sua mesa)
    players = {
        "player_0_name":  (50,  50,  140, 25),
        "player_0_stack": (50,  80,  140, 25),
        "player_1_name":  (300, 50,  140, 25),
        "player_1_stack": (300, 80,  140, 25),
        "player_2_name":  (550, 50,  140, 25),
        "player_2_stack": (550, 80,  140, 25),
        "player_3_name":  (550, 250, 140, 25),
        "player_3_stack": (550, 280, 140, 25),
        "player_4_name":  (300, 350, 140, 25),
        "player_4_stack": (300, 380, 140, 25),
        "player_5_name":  (50,  350, 140, 25),
        "player_5_stack": (50,  380, 140, 25),
        # etc.
    }

    # Pote principal (geralmente fica no centro)
    pot = (350, 200, 100, 30)

    # Board (cartas comunitárias) – se quiser OCR do valor escrito
    # ou use template matching para naipes. Exemplo de 5 cartas:
    board_cards = {
        "card_0": (250, 180, 40, 60),
        "card_1": (300, 180, 40, 60),
        "card_2": (350, 180, 40, 60),
        "card_3": (400, 180, 40, 60),
        "card_4": (450, 180, 40, 60),
    }

    # Cartas do Hero (jogador local), se precisar
    hero_cards = {
        "hero_card_0": (330, 300, 40, 60),
        "hero_card_1": (380, 300, 40, 60),
    }

    # Botões de ação (para detectar se aparecem "PAGAR", "DESISTIR", etc.)
    actions = {
        "fold_btn":    (700, 400, 80, 30),
        "call_btn":    (800, 400, 80, 30),
        "raise_btn":   (900, 400, 80, 30),
    }

    # Informações de mesa (ID da mesa, blinds, etc.)
    table_info = {
        "table_id": (20, 10, 200, 30),
    }
