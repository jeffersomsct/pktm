import sys
import re
import os
from dataclasses import dataclass
from typing import List, Dict, Optional
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton,
                              QVBoxLayout, QHBoxLayout, QListWidget,
                              QGraphicsScene, QGraphicsView, QLabel,  QTableWidget,
                              QTableWidgetItem, QHeaderView)
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

class Street(Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"

@dataclass
class Action:
    player: str
    type: ActionType
    street: Street
    amount: float = 0
    total: float = 0
    cards: List[str] = None
    pot: float = 0

@dataclass
class Hand:
    id: str
    players: Dict[int, dict]
    actions: List[Action]
    board: Dict[Street, List[str]]  # Modificado para mapear ruas para cartas
    button_seat: int = 1
    total_pot: float = 0
    current_street: Street = Street.PREFLOP

class HandParser:
    @staticmethod
    def parse_action(line: str, player: str, action_type: str, current_pot: float, current_street: Street) -> Action:
        amount = 0
        total = 0
        cards = None

        if "posts" in line:
            amount_match = re.search(r"posts (?:small blind|big blind|ante) (\d+\.?\d*)", line)
            if amount_match:
                amount = float(amount_match.group(1))
        elif "calls" in line:
            amount_match = re.search(r"calls (\d+\.?\d*)", line)
            if amount_match:
                amount = float(amount_match.group(1))
        elif "bets" in line:
            amount_match = re.search(r"bets (\d+\.?\d*)", line)
            if amount_match:
                amount = float(amount_match.group(1))
        elif "raises" in line:
            amount_match = re.search(r"raises (\d+\.?\d*) to (\d+\.?\d*)", line)
            if amount_match:
                amount = float(amount_match.group(1))
                total = float(amount_match.group(2))
        elif "shows" in line:
            cards_match = re.search(r"\[(.*?)\]", line)
            if cards_match:
                cards = cards_match.group(1).split()
        elif "collected" in line:
            amount_match = re.search(r"collected \((\d+\.?\d*)\)", line)
            if amount_match:
                amount = float(amount_match.group(1))

        return Action(
            player=player,
            type=ActionType(action_type),
            street=current_street,
            amount=amount,
            total=total,
            cards=cards,
            pot=current_pot
        )
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
        hand = Hand(
            id="",
            players={},
            actions=[],
            board={street: [] for street in Street},
            current_street=Street.PREFLOP
        )

        current_pot = 0.0
        current_street = Street.PREFLOP

        for line in lines:
            # Parse street markers and update current street
            if "*** HOLE CARDS ***" in line:
                current_street = Street.PREFLOP
            elif "*** FLOP ***" in line:
                current_street = Street.FLOP
                cards_match = re.search(r"\[(.*?)\]", line)
                if cards_match:
                    hand.board[Street.FLOP] = cards_match.group(1).split()
            elif "*** TURN ***" in line:
                current_street = Street.TURN
                cards_match = re.search(r"\] \[(.*?)\]", line)
                if cards_match:
                    hand.board[Street.TURN] = [cards_match.group(1)]
            elif "*** RIVER ***" in line:
                current_street = Street.RIVER
                cards_match = re.search(r"\] \[(.*?)\]", line)
                if cards_match:
                    hand.board[Street.RIVER] = [cards_match.group(1)]
            elif "*** SUMMARY ***" in line:
                current_street = Street.SHOWDOWN
                break

            # Parse hand ID and table info
            hand_id_match = re.search(r'Hand #(\d+)', line)
            if hand_id_match:
                hand.id = hand_id_match.group(1)
            if hand.id == 188233028:
                pass
            table_match = re.match(r"Table '.*' \d-max Seat #(\d) is the button", line)
            if table_match:
                hand.button_seat = int(table_match.group(1))

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

            # Parse actions
            action_match = re.match(r"(\w+): (posts|folds|calls|raises|bets|checks|shows|collected)", line)
            if action_match:
                player, action_type = action_match.groups()
                action = HandParser.parse_action(line, player, action_type, current_pot, current_street)

                # Update current pot
                if action.type in [ActionType.POSTS, ActionType.CALLS, ActionType.BETS]:
                    current_pot += action.amount
                elif action.type == ActionType.RAISES:
                    current_pot += action.total

                hand.actions.append(action)

        return hand

class HandHistoryTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Poker Hand", "Hero Cards", "Board Cards", "$ Pot"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def add_hand(self, hand: Hand, hero_name: str):
        row = self.rowCount()
        self.insertRow(row)

        # Poker Hand ID
        self.setItem(row, 0, QTableWidgetItem(str(hand.id)))

        # Hero Cards
        hero_cards = ""
        for player in hand.players.values():
            if player['name'] == hero_name and player['cards']:
                hero_cards = self.format_cards(player['cards'])
        self.setItem(row, 1, QTableWidgetItem(hero_cards))

        # Board Cards
        board_cards = []
        for street in [Street.FLOP, Street.TURN, Street.RIVER]:
            if hand.board[street]:
                board_cards.extend(hand.board[street])
        self.setItem(row, 2, QTableWidgetItem(self.format_cards(board_cards)))

        # Pot
        self.setItem(row, 3, QTableWidgetItem(f"${hand.total_pot:.2f}"))

    def format_cards(self, cards: List[str]) -> str:
        if not cards:
            return ""

        formatted = []
        for card in cards:
            suit = card[-1]
            color = {
                'h': '#FF0000',  # Hearts - Red
                'd': '#0000FF',  # Diamonds - Blue
                'c': '#00FF00',  # Clubs - Green
                's': '#000000'   # Spades - Black
            }.get(suit.lower(), '#000000')

            formatted.append(f'<span style="color: {color}">{card}</span>')

        return ' '.join(formatted)

class PokerTable(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)

        self.table_width = 600
        self.table_height = 400
        self.setMinimumSize(self.table_width + 50, self.table_height + 50)
        self.action_text_items = []
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

        self.dealer_button = QPixmap(os.path.join('replay_system/cards/',"dealersmall.png"))
        if self.dealer_button.isNull():
            print("Failed to load dealer button image!")

        # Position markers
        self.position_colors = {
            'SB': QColor("#FFD700"),  # Yellow
            'BB': QColor("#FFD700"),  # Yellow
            'BTN': QColor("#00FF00"), # Green
            'CO': QColor("#00FF00"),  # Green
            'MP1': QColor("#0000FF"), # Blue
            'MP2': QColor("#0000FF"), # Blue
            'HJ': QColor("#0000FF"),  # Blue
            'UTG': QColor("#FF0000"), # Red
            'UTG+1': QColor("#FF0000"), # Red
            'UTG+2': QColor("#FF0000")  # Red
        }

        self.reset_state()
        self.current_street = Street.PREFLOP

    def get_positions(self, num_players: int) -> Dict[int, str]:
        positions = {}
        if num_players == 10:
            positions = {1:'SB', 2:'BB', 3:'UTG', 4:'UTG+1', 5:'UTG+2',
                        6:'MP1', 7:'MP2', 8:'HJ', 9:'CO', 10:'BTN'}
        elif num_players == 9:
            positions = {1:'SB', 2:'BB', 3:'UTG', 4:'UTG+1', 5:'MP1',
                        6:'MP2', 7:'HJ', 8:'CO', 9:'BTN'}
        # ... (add other position mappings)

        return positions

    def draw_action_text(self, action: Action):
        """Draw action text near the player"""
        # Find player position
        player_pos = None
        for seat, player in self.players.items():
            if player['name'] == action.player:
                player_pos = self.seat_positions[seat]
                break

        if not player_pos:
            return

        # Create action text
        text = f"{action.type.value}"
        if action.amount > 0:
            if action.type == ActionType.RAISES:
                text += f" {action.amount} to {action.total}"
            else:
                text += f" {action.amount}"

        # Create and position text item
        text_item = self.scene.addText(text)
        text_item.setDefaultTextColor(Qt.white)
        # Offset the text to not overlap with player info
        text_item.setPos(player_pos.x() + 70, player_pos.y())

        # Add to list of action texts to clear them later
        self.action_text_items.append(text_item)

    def update_player_states(self, action: Action):
        """Update player states based on the current action"""
        if action.type == ActionType.FOLDS:
            # Mark player as folded
            for seat, player in self.players.items():
                if player['name'] == action.player:
                    player['folded'] = True
                    break
        elif action.type in [ActionType.CALLS, ActionType.BETS, ActionType.RAISES, ActionType.POSTS]:
            # Update player's current bet and chips
            for player in self.players.values():
                if player['name'] == action.player:
                    if action.type == ActionType.RAISES:
                        player['current_bet'] = action.total
                        player['chips'] -= action.total
                    else:
                        player['current_bet'] = action.amount
                        player['chips'] -= action.amount
                    break

            # Update pot
            if action.type == ActionType.RAISES:
                self.pot += action.total
            else:
                self.pot += action.amount
        elif action.type == ActionType.SHOWS:
            # Show player's cards
            for player in self.players.values():
                if player['name'] == action.player:
                    player['cards'] = action.cards
                    break

        # Keep bets visible until end of street
        if action.street != self.current_street:
            for player in self.players.values():
                player['current_bet'] = 0

        # Highlight winner at showdown
        if action.type == ActionType.COLLECTS:
            for player in self.players.values():
                player['winner'] = player['name'] == action.player


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

        if hasattr(self, 'current_hand') and self.current_street == Street.PREFLOP:
            positions = self.get_positions(len(self.players))
            if seat in positions:
                pos_marker = QRectF(pos.x() - 20, pos.y() - 60, 40, 20)
                self.scene.addRect(pos_marker,
                                 QPen(Qt.black),
                                 QBrush(self.position_colors[positions[seat]]))
                text = self.scene.addText(positions[seat])
                text.setDefaultTextColor(Qt.black)
                text.setPos(pos.x() - 15, pos.y() - 60)

        # Draw dealer button if this is the button seat
        if hasattr(self, 'current_hand') and seat == self.current_hand.button_seat:
            dealer_item = self.scene.addPixmap(self.dealer_button)
            dealer_item.setPos(pos.x() - 30, pos.y() - 50)

        # Draw sitting out status if applicable
        if player_info.get('sitting_out', False):
            text_rect = QRectF(pos.x() - 40, pos.y() + 40, 80, 20)
            self.scene.addRect(text_rect, QPen(Qt.black), QBrush(Qt.red))
            text = self.scene.addText("Sitting Out")
            text.setDefaultTextColor(Qt.white)
            text.setPos(pos.x() - 35, pos.y() + 40)

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

        # Update current street
        if action.street != self.current_street:
            self.current_street = action.street
            # Update community cards based on the new street
            self.community_cards = []
            if self.current_street == Street.FLOP:
                self.community_cards = self.current_hand.board[Street.FLOP]
            elif self.current_street == Street.TURN:
                self.community_cards = (
                    self.current_hand.board[Street.FLOP] +
                    self.current_hand.board[Street.TURN]
                )
            elif self.current_street == Street.RIVER:
                self.community_cards = (
                    self.current_hand.board[Street.FLOP] +
                    self.current_hand.board[Street.TURN] +
                    self.current_hand.board[Street.RIVER]
                )

        # Update player states
        self.update_player_states(action)
        self.draw_table()
        return True

    def set_hand(self, hand: Hand):
        self.current_hand = hand
        self.current_action_idx = -1
        self.players = hand.players.copy()
        self.community_cards = []
        self.pot = 0
        self.current_street = Street.PREFLOP

        # Initialize player states
        for player in self.players.values():
            player['folded'] = False
            player['cards'] = []
            player['current_bet'] = 0

        self.draw_table()
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
        # Clear previous action texts
        for item in self.action_text_items:
            self.scene.removeItem(item)
        self.action_text_items.clear()

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

        # If there's a current action, draw its text
        if hasattr(self, 'current_hand') and self.current_hand and self.current_action_idx >= 0:
            current_action = self.current_hand.actions[self.current_action_idx]
            self.draw_action_text(current_action)

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

        # Add hand history table
        self.hand_history = HandHistoryTable()
        sidebar_layout.addWidget(QLabel("Hand History:"))
        sidebar_layout.addWidget(self.hand_history)

    def load_log_file(self, filename):
        with open(filename, 'r', encoding='utf-8') as f:
            text = f.read()
            self.hands = HandParser.parse_hands_from_file(text)

        self.hand_list.clear()
        for hand in self.hands:
            # Fix the board display in the hand list
            text = f"{hand.id}"
            # Convert board cards to a readable format
            board_cards = []
            for street in [Street.FLOP, Street.TURN, Street.RIVER]:
                if hand.board[street]:
                    board_cards.extend(hand.board[street])
            if board_cards:
                text += f" - Board: {' '.join(board_cards)}"
            self.hand_list.addItem(text)

        if self.hands:
            self.select_hand(self.hand_list.item(0))

        # Update hand history table
        self.hand_history.setRowCount(0)
        for hand in self.hands:
            self.hand_history.add_hand(hand, "Jeffersom")

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