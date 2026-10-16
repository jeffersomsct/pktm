import sys
import re
import os
from dataclasses import dataclass
from typing import List, Dict, Optional
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton, 
                              QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
                              QGraphicsScene, QGraphicsView, QLabel)
from PySide6.QtGui import QPainter, QBrush, QPen, QColor, QPolygonF, QFont, QPainterPath, QPixmap
from PySide6.QtCore import Qt, QPointF, QRectF, QTimer
from PySide6.QtWidgets import QSlider
from enum import Enum

class ActionType(Enum):
    POSTS = "posts"
    FOLDS = "folds"
    CALLS = "calls"
    RAISES = "raises"
    BETS = "bets"
    CHECKS = "checks"
    SHOWS = "shows"
    COLLECTS = "collected"

@dataclass
class Action:
    player: str
    type: ActionType
    amount: float = 0
    total: float = 0
    cards: List[str] = None
    pot: float = 0

@dataclass
class Hand:
    id: str
    players: Dict[int, dict]
    actions: List[Action]
    board: List[str]
    button_seat: int = 1
    total_pot: float = 0

class HandParser:
    @staticmethod
    def parse_hands_from_file(text: str) -> List[Hand]:
        hands = []
        current_hand_lines = []
        
        for line in text.split('\n'):
            if 'Hand #' in line and current_hand_lines:
                hands.append(HandParser.parse_single_hand(current_hand_lines))
                current_hand_lines = []
            current_hand_lines.append(line)
            
        if current_hand_lines:
            hands.append(HandParser.parse_single_hand(current_hand_lines))
            
        return hands

    @staticmethod
    def parse_single_hand(lines: List[str]) -> Hand:
        hand = Hand(id="", players={}, actions=[], board=[])
        
        # Parse hand ID
        hand_id_match = re.search(r'Hand #(\d+)', lines[0])
        if hand_id_match:
            hand.id = hand_id_match.group(1)
        
        # Parse table info and button position
        table_match = re.match(r"Table '.*' \d-max Seat #(\d) is the button", lines[0])
        if not table_match:
            for line in lines:
                table_match = re.match(r"Table '.*' \d-max Seat #(\d) is the button", line)
                if table_match:
                    hand.button_seat = int(table_match.group(1))
                    break
        else:
            hand.button_seat = int(table_match.group(1))
            
        current_pot = 0.0
        
        for line in lines:
            fim = re.fullmatch(r"\*\*\* SUMMARY \*\*\*", line)
            if fim:
                break
            
            # Parse seats
            seat_match = re.match(r"Seat (\d): (\w+) \((\d+\.?\d*) in chips\)", line)
            if seat_match:
                seat_num, name, chips = seat_match.groups()
                hand.players[int(seat_num)] = {
                    "name": name,
                    "chips": float(chips),
                    "cards": [],
                    "current_bet": 0.0
                }
                continue

            # Parse community cards
            if "*** FLOP ***" in line:
                cards_match = re.search(r"\[(.*?)\]", line)
                if cards_match:
                    hand.board.extend(cards_match.group(1).split())
                continue
                
            if "*** TURN ***" in line:
                cards_match = re.search(r"\] \[(.*?)\]", line)
                if cards_match:
                    hand.board.append(cards_match.group(1))
                continue
                
            if "*** RIVER ***" in line:
                cards_match = re.search(r"\] \[(.*?)\]", line)
                if cards_match:
                    hand.board.append(cards_match.group(1))
                continue

            # Parse actions
            action_match = re.match(r"(\w+): (posts|folds|calls|raises|bets|checks|shows|collected)", line)
            if action_match:
                player, action_type = action_match.groups()
                amount = 0
                total = 0
                cards = None
                
                if "posts" in line:
                    # Match specifically the pattern after "posts"
                    amount_match = re.search(r"posts (?:small blind|big blind|ante) (\d+\.?\d*)", line)
                    if amount_match:
                        amount = float(amount_match.group(1))
                        current_pot += amount
                elif "calls" in line:
                    # Match amount after "calls"
                    amount_match = re.search(r"calls (\d+\.?\d*)", line)
                    if amount_match:
                        amount = float(amount_match.group(1))
                        current_pot += amount
                elif "bets" in line:
                    # Match amount after "bets"
                    amount_match = re.search(r"bets (\d+\.?\d*)", line)
                    if amount_match:
                        amount = float(amount_match.group(1))
                        current_pot += amount
                elif "raises" in line:
                    # Match both amounts in raise pattern: "raises X to Y"
                    amount_match = re.search(r"raises (\d+\.?\d*) to (\d+\.?\d*)", line)
                    if amount_match:
                        amount = float(amount_match.group(1))  # raise amount
                        total = float(amount_match.group(2))   # total amount
                        current_pot += total
                elif "shows" in line:
                    # Match cards between brackets
                    cards_match = re.search(r"\[(.*?)\]", line)
                    if cards_match:
                        cards = cards_match.group(1).split()
                elif "collected" in line:
                    # Match amount between parentheses after "collected"
                    amount_match = re.search(r"collected \((\d+\.?\d*)\)", line)
                    if amount_match:
                        amount = float(amount_match.group(1))
                
                action = Action(
                    player=player,
                    type=ActionType(action_type),
                    amount=amount,
                    total=total,
                    cards=cards,
                    pot=current_pot
                )
                hand.actions.append(action)
                
        return hand

class PokerTable(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        
        self.table_width = 600
        self.table_height = 400
        self.setMinimumSize(self.table_width + 50, self.table_height + 50)
        
        self.seat_positions = {
            1: QPointF(self.table_width/2, self.table_height - 50),      # Bottom
            2: QPointF(100, self.table_height - 100),                    # Bottom Left
            3: QPointF(50, self.table_height/2),                         # Left
            4: QPointF(100, 100),                                        # Top Left
            5: QPointF(self.table_width/2, 50),                         # Top
            6: QPointF(self.table_width - 100, 100),                    # Top Right
            7: QPointF(self.table_width - 50, self.table_height/2)      # Right
        }
        
        # Load card images
        self.card_images = {}
        cards_path = "replay_system/cards/"  # Update this path to your cards directory
        if os.path.exists(cards_path):
            for suit in ['c', 'd', 'h', 's']:
                for rank in ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']:
                    card_name = f"{rank}{suit}"
                    image_path = os.path.join(cards_path, f"{card_name}.png")
                    if os.path.exists(image_path):
                        self.card_images[card_name] = QPixmap(image_path)
        
        self.card_back = QPixmap(os.path.join('replay_system/cards/', "cardverso.png"))
        if self.card_back.isNull():
            print("Falha ao carregar a imagem!")
        self.reset_state()

    def draw_card(self, card_code: str, pos: QPointF, is_back: bool = False):
        if is_back:
            pixmap = self.card_back
        elif card_code in self.card_images:
            pixmap = self.card_images[card_code]
        else:
            pixmap = self.card_back
            
        scaled_pixmap = pixmap.scaled(40, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        card_item = self.scene.addPixmap(scaled_pixmap)
        card_item.setPos(pos)

    def draw_player(self, player_info: dict, seat: int):
        pos = self.seat_positions[seat]
        
        # Determine if this player is active
        is_active = False
        if self.current_hand and self.current_action_idx >= 0:
            current_action = self.current_hand.actions[self.current_action_idx]
            is_active = current_action.player == player_info['name']
        
        # Draw player info box with highlight if active
        seat_rect = QRectF(pos.x() - 60, pos.y() - 40, 120, 80)
        border_color = QColor("#FFD700") if is_active else Qt.black
        border_width = 3 if is_active else 1
        self.scene.addRect(seat_rect, 
                          QPen(border_color, border_width), 
                          QBrush(QColor("#2c3e50")))
        
        # Show player name, chips and current bet if any
        text = f"{player_info['name']}\n${player_info['chips']:.2f}"
        if player_info['current_bet'] > 0:
            text += f"\nBet: ${player_info['current_bet']:.2f}"
        
        text_item = self.scene.addText(text)
        text_item.setDefaultTextColor(Qt.white)
        text_item.setPos(pos.x() - 50, pos.y() - 30)
        
        # Draw player cards
        if player_info.get('folded', False):
            return
            
        if player_info['cards']:
            # Show actual cards
            card_width = 40
            start_x = pos.x() - (card_width + 5)
            for i, card in enumerate(player_info['cards']):
                card_x = start_x + (i * (card_width + 10))
                self.draw_card(card, QPointF(card_x, pos.y() - 30))
        elif not player_info.get('folded', False):
            # Show card backs if player is still in hand
            card_width = 40
            start_x = pos.x() - (card_width + 5)
            for i in range(2):  # Draw two card backs
                card_x = start_x + (i * (card_width + 10))
                self.draw_card("", QPointF(card_x, pos.y() - 30), is_back=True)

    def draw_community_cards(self):
        if not self.community_cards:
            return

        start_x = (self.table_width - (len(self.community_cards) * 50)) / 2
        y = self.table_height / 2 - 30

        for i, card in enumerate(self.community_cards):
            self.draw_card(card, QPointF(start_x + (i * 50), y))

    def next_action(self) -> bool:
        if not self.current_hand or self.current_action_idx >= len(self.current_hand.actions) - 1:
            return False
            
        self.current_action_idx += 1
        action = self.current_hand.actions[self.current_action_idx]
        
        # Update state based on action
        if action.type == ActionType.POSTS or action.type == ActionType.CALLS or action.type == ActionType.BETS:
            for seat, player in self.players.items():
                if player['name'] == action.player:
                    player['chips'] -= action.amount
                    player['current_bet'] = action.amount
            self.pot = action.pot
        elif action.type == ActionType.RAISES:
            for seat, player in self.players.items():
                if player['name'] == action.player:
                    player['chips'] -= action.total
                    player['current_bet'] = action.total
            self.pot = action.pot
        elif action.type == ActionType.SHOWS:
            for seat, player in self.players.items():
                if player['name'] == action.player:
                    player['cards'] = action.cards
        elif action.type == ActionType.FOLDS:
            for seat, player in self.players.items():
                if player['name'] == action.player:
                    player['folded'] = True
        elif action.type == ActionType.COLLECTS:
            for seat, player in self.players.items():
                if player['name'] == action.player:
                    player['chips'] += action.amount
        
        # Update community cards based on street
        street_count = len(self.current_hand.board)
        if street_count >= 3 and len(self.community_cards) < 3:  # Flop
            self.community_cards = self.current_hand.board[:3]
        elif street_count >= 4 and len(self.community_cards) == 3:  # Turn
            self.community_cards.append(self.current_hand.board[3])
        elif street_count == 5 and len(self.community_cards) == 4:  # River
            self.community_cards.append(self.current_hand.board[4])
                    
        self.draw_table()
        return True

    def set_hand(self, hand: Hand):
        self.current_hand = hand
        self.current_action_idx = -1
        self.players = hand.players.copy()
        self.community_cards = []
        self.pot = 0
        
        # Initialize folded status for all players
        for player in self.players.values():
            player['folded'] = False
            
        self.draw_table()

    def draw_table(self):
        self.scene.clear()
        
        # Draw poker table
        table_brush = QBrush(QColor("#076324"))
        table_pen = QPen(QColor("#4a3728"), 15)
        path = QPainterPath()
        path.addEllipse(25, 25, self.table_width - 50, self.table_height - 50)
        self.scene.addPath(path, table_pen, table_brush)
        
        # Draw pot amount
        if self.pot > 0:
            pot_text = self.scene.addText(f"Pot: ${self.pot:.2f}")
            pot_text.setDefaultTextColor(Qt.white)
            pot_text.setPos(self.table_width/2 - 40, self.table_height/2 - 60)
        
        # Draw players
        for seat_num, player_info in self.players.items():
            self.draw_player(player_info, seat_num)
            
        # Draw community cards
        self.draw_community_cards()
    
    def reset_state(self):
        self.current_hand = None
        self.current_action_idx = -1
        self.players = {}
        self.community_cards = []
        self.pot = 0
        self.draw_table()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Poker Hand Replay")
        self.resize(1000, 700)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Create poker table view
        self.poker_table = PokerTable()
        layout.addWidget(self.poker_table)
        
        # Create right sidebar
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        layout.addWidget(sidebar)
        
        # Add controls
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        
        self.play_button = QPushButton("Play")
        self.prev_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(5)
        
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.prev_button)
        controls_layout.addWidget(self.next_button)
        controls_layout.addWidget(QLabel("Speed:"))
        controls_layout.addWidget(self.speed_slider)
        
        sidebar_layout.addWidget(controls)
        
        # Add hand list
        self.hand_list = QListWidget()
        sidebar_layout.addWidget(QLabel("Hand History:"))
        sidebar_layout.addWidget(self.hand_list)
        
        # Timer for auto-play
        self.play_timer = QTimer()
        self.play_timer.timeout.connect(self.auto_next_action)
        
        # Connect signals
        self.play_button.clicked.connect(self.toggle_play)
        self.next_button.clicked.connect(self.next_action)
        self.prev_button.clicked.connect(self.prev_action)
        self.hand_list.itemClicked.connect(self.select_hand)
        
        # Load hands
        self.hands = []
        self.current_hand_index = -1
    
    def load_log_file(self, filename):
        with open(filename, 'r', encoding='utf-8') as f:
            text = f.read()
            self.hands = HandParser.parse_hands_from_file(text)
            
        self.hand_list.clear()
        for hand in self.hands:
            text = f"Hand #{hand.id}"
            if hand.board:
                text += f" - Board: {' '.join(hand.board)}"
            self.hand_list.addItem(text)
            
        if self.hands:
            self.select_hand(self.hand_list.item(0))
        
    def toggle_play(self):
        if self.play_timer.isActive():
            self.play_timer.stop()
            self.play_button.setText("Play")
        else:
            self.play_timer.start(1000 // self.speed_slider.value())
            self.play_button.setText("Pause")
        
    def auto_next_action(self):
        if not self.poker_table.next_action():
            self.play_timer.stop()
            self.play_button.setText("Play")
            
    def next_action(self):
        self.poker_table.next_action()
        
    def prev_action(self):
        if self.poker_table.current_action_idx > 0:
            self.poker_table.current_action_idx -= 1
            # Reset and replay all actions up to current index
            self.poker_table.set_hand(self.poker_table.current_hand)
            for _ in range(self.poker_table.current_action_idx):
                self.poker_table.next_action()
                
    def select_hand(self, item):
        index = self.hand_list.row(item)
        if 0 <= index < len(self.hands):
            self.current_hand_index = index
            self.poker_table.set_hand(self.hands[index])

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    log_file_path = "D:/CoinPoker/log/log_example.log"  # Ajuste para o caminho do seu arquivo
    
    try:
        window.load_log_file(log_file_path)
    except FileNotFoundError:
        print(f"Arquivo não encontrado: {log_file_path}")
    except Exception as e:
        print(f"Erro ao carregar o arquivo: {e}")
    
    sys.exit(app.exec())