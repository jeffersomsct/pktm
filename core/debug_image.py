"""
core/debug_image.py
Visualizacao de debug: desenha ROIs, cartas, posicoes e labels na imagem.

Migracao da versao anterior:
  - player.position -> player.seat
  - community_cards: List[tuple] -> List[Card] (usar card.rank / card.suit)
"""
import numpy as np
import cv2
from typing import List

from core.models import Card


_SUIT_EMOJIS = {
    'S': '♠',
    'H': '♥',
    'D': '♦',
    'C': '♣',
}


def _card_rank_suit(card_or_tuple):
    """Aceita tanto Card dataclass quanto tuple (rank, suit) por compat."""
    if isinstance(card_or_tuple, Card):
        return card_or_tuple.rank, card_or_tuple.suit
    if isinstance(card_or_tuple, (tuple, list)) and len(card_or_tuple) >= 2:
        return card_or_tuple[0], card_or_tuple[1]
    return "?", "?"


def create_debug_image(
    image: np.ndarray,
    config,
    dealer_position: int,
    players: list,
    community_cards: List = None,
    player_positions: dict = None,
):
    """
    Cria imagem de debug com todas as ROIs e informacoes reconhecidas.

    Args:
        image: snapshot BGR.
        config: RoomConfig com roi_config, dealer_config.
        dealer_position: seat do dealer (-1 se nao detectado).
        players: List[Player].
        community_cards: List[Card] (ou List[tuple] por compat).
        player_positions: dict opcional {name: PlayerPositionInfo}
            (legado; info ja esta em Player.pos_preflop).
    """
    debug_image = image.copy()
    roi_config = config.roi_config

    # ---- Cartas comunitarias ----
    if hasattr(roi_config, "ranks") and hasattr(roi_config, "suits"):
        for i in range(1, 6):  # flop, turn, river
            rank_roi = getattr(roi_config.ranks, f"rank_{i}", None)
            suit_roi = getattr(roi_config.suits, f"suit_{i}", None)

            card_text = ""
            card_info = ""
            if community_cards and i <= len(community_cards):
                rank, suit = _card_rank_suit(community_cards[i - 1])
                card_text = f"{rank}{_SUIT_EMOJIS.get(suit, suit)}"
                card_info = f"Card {i}: {rank}{suit}"

            # ROI do rank
            if rank_roi:
                x, y, w, h = rank_roi
                cv2.rectangle(debug_image, (x, y), (x + w, y + h),
                              (0, 165, 255), 2)
                if card_text:
                    (text_w, text_h), _ = cv2.getTextSize(
                        card_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                    cv2.rectangle(debug_image,
                                  (x, y - text_h - 10),
                                  (x + text_w + 10, y), (0, 0, 0), -1)
                    cv2.putText(debug_image, card_text, (x + 5, y - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                                (0, 255, 255), 2)

            # ROI do naipe
            if suit_roi:
                x, y, w, h = suit_roi
                cv2.rectangle(debug_image, (x, y), (x + w, y + h),
                              (255, 0, 255), 2)
                if card_text and len(card_text) > 1:
                    suit_char = card_text[-1]
                    (text_w, text_h), _ = cv2.getTextSize(
                        suit_char, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                    cv2.rectangle(debug_image,
                                  (x, y - text_h - 10),
                                  (x + text_w + 10, y), (0, 0, 0), -1)
                    cv2.putText(debug_image, suit_char, (x + 5, y - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                                (0, 255, 255), 2)

            if card_info:
                cv2.putText(debug_image, card_info,
                            (10, 30 + (i - 1) * 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                            (0, 255, 255), 2)

    # ---- Stacks ----
    for name, (x, y, w, h) in config.roi_config.stacks.items():
        cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 1)
        seat_idx = int(name.split("_")[1])
        stack_value = players[seat_idx].stack if seat_idx < len(players) else 0
        cv2.putText(debug_image, f"Stack: {stack_value}",
                    (x, y + h + 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # ---- Bets ----
    for name, (x, y, w, h) in config.roi_config.bets.items():
        cv2.rectangle(debug_image, (x, y), (x + w, y + h), (255, 0, 0), 1)
        seat_idx = int(name.split("_")[1])
        bet_value = (players[seat_idx].current_bet
                     if seat_idx < len(players) else 0)
        cv2.putText(debug_image, f"Bet: {bet_value}", (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    # ---- Names + positions ----
    for name, (x, y, w, h) in config.roi_config.names.items():
        cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 0, 255), 1)
        seat_idx = int(name.split("_")[1])
        player_name = (players[seat_idx].name
                       if seat_idx < len(players) else "")

        # Posicao pre-flop: vem direto do Player
        position_text = ""
        if seat_idx < len(players):
            p = players[seat_idx]
            if p.pos_preflop and hasattr(p.pos_preflop, "value"):
                position_text = p.pos_preflop.value
            elif player_positions and player_name in player_positions:
                # Fallback legado
                pos_info = player_positions[player_name]
                if hasattr(pos_info.position_name, "value"):
                    position_text = pos_info.position_name.value

        font = cv2.FONT_HERSHEY_DUPLEX
        font_scale = 0.6
        thickness = 1
        text_color = (200, 255, 200)
        bg_color = (40, 40, 40)

        text = f"{player_name}"
        (text_width, text_height), baseline = cv2.getTextSize(
            text, font, font_scale, thickness)

        # Texto da posicao (acima do nome)
        if position_text:
            pos_font_scale = 0.5
            pos_thickness = 1
            pos_color = (255, 200, 100)
            pos_bg_color = (60, 40, 20)
            (pos_text_width, pos_text_height), _ = cv2.getTextSize(
                position_text, font, pos_font_scale, pos_thickness)
            pos_bg_x1 = x
            pos_bg_y1 = y - text_height - 10 - pos_text_height - 8
            pos_bg_x2 = x + pos_text_width
            pos_bg_y2 = y - text_height - 12
            cv2.rectangle(debug_image,
                          (pos_bg_x1, pos_bg_y1),
                          (pos_bg_x2, pos_bg_y2),
                          pos_bg_color, -1)
            cv2.putText(debug_image, position_text,
                        (x, y - text_height - 15),
                        font, pos_font_scale, pos_color,
                        pos_thickness, lineType=cv2.LINE_AA)

        bg_x1 = x
        bg_y1 = y - text_height - 10
        bg_x2 = x + text_width
        bg_y2 = y - 5
        cv2.rectangle(debug_image,
                      (bg_x1, bg_y1),
                      (bg_x2, bg_y2),
                      bg_color, -1)
        cv2.putText(debug_image, text, (x, y - 8),
                    font, font_scale, text_color,
                    thickness, lineType=cv2.LINE_AA)

    # ---- Pot ----
    for name, (x, y, w, h) in config.roi_config.pot.items():
        cv2.rectangle(debug_image, (x, y), (x + w, y + h), (255, 255, 0), 1)
        cv2.putText(debug_image, "Pot", (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

    # ---- Hand ID ----
    for name, (x, y, w, h) in config.roi_config.hand.items():
        cv2.rectangle(debug_image, (x, y), (x + w, y + h),
                      (255, 255, 150), 1)
        cv2.putText(debug_image, "Hand", (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

    # ---- Small pot ----
    for name, (x, y, w, h) in config.roi_config.smallpot.items():
        cv2.rectangle(debug_image, (x, y), (x + w, y + h),
                      (0, 255, 255), 1)
        cv2.putText(debug_image, "Small Pot", (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

    # ---- Dealer ----
    if dealer_position != -1 and dealer_position in config.dealer_config.positions:
        x, y = config.dealer_config.positions[dealer_position]
        cv2.circle(debug_image, (x, y), 3, (0, 100, 255), -1)
        cv2.putText(debug_image, f"Dealer {dealer_position}",
                    (x + 10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    # ---- SB / BB markers ----
    for player in players:
        pos_label = ""
        if player.pos_preflop and hasattr(player.pos_preflop, "value"):
            pos_label = player.pos_preflop.value
        if pos_label in ("SB", "BB"):
            if player.seat in config.dealer_config.positions:
                x, y = config.dealer_config.positions[player.seat]
                color = (0, 255, 255) if pos_label == "SB" else (150, 200, 0)
                cv2.circle(debug_image, (x, y), 5, color, -1)
                cv2.putText(debug_image, pos_label, (x + 10, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # ---- Hero marker ----
    for player in players:
        if player.is_hero:
            if player.seat in config.dealer_config.positions:
                x, y = config.dealer_config.positions[player.seat]
                cv2.circle(debug_image, (x, y), 8, (0, 255, 255), 2)
                cv2.putText(debug_image, "HERO", (x + 12, y - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

    # ---- ROIs base rank/suit (templates) ----
    if hasattr(roi_config, "ranks") and hasattr(roi_config, "suits"):
        x, y, w, h = roi_config.ranks["rank"]
        cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 1)
        cv2.putText(debug_image, "rank", (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        x, y, w, h = roi_config.suits["suit"]
        cv2.rectangle(debug_image, (x, y), (x + w, y + h), (255, 0, 0), 1)
        cv2.putText(debug_image, "suit", (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

    print("Debug Mode ON: Image save: debug_table_recognition.png")
    cv2.imwrite("debug_table_recognition.png", debug_image)
