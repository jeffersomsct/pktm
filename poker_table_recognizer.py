"""
poker_table_recognizer.py
Reconhecimento visual da mesa (CV): template matching, ROIs, OCR.

Migracao pra estrutura refatorada (8 pontos aplicados):
  1. SEM dataclasses locais e SEM TableState -- tudo vem de core.models;
  2. CharacterRecognizer inalterado (CV de template matching que funciona);
  3. Player construido com seat= (antes position=);
  4. process_table() retorna TableInfo DIRETO -- variaveis locais corretas
     (hand_id / dealer_position / community_cards / bb_positions);
  5. BlindsManager removido -- usa core.blinds.validate_preflop_bets
     (por valor apostado) com fallback geometrico pelo button;
  6. pot/small_pot como float via convert_to_float (tolera "" e lixo de OCR;
     float("") direto levantava ValueError);
  7. community_cards como List[Card] com rank/suit validados (zip evita
     IndexError quando OCR de rank e suit tem tamanhos diferentes);
  8. Campos novos preenchidos quando possivel: bb_positions, sb_amount,
     bb_amount, snapshot_path. hero/shown_cards/pots ficam pra uma proxima
     iteracao (exigem novas ROIs/templates na config).
"""
import numpy as np
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional
import cv2

from config.room_config import DetectionMethod, RoomConfig
from config.pixel_detector import detect_pixels_in_window
from config.templates import discover_templates

from core.models import Player, TableInfo, Card, Position
from core.blinds import validate_preflop_bets
from core.debug_image import create_debug_image


VALID_RANKS = set("23456789TJQKA")
VALID_SUITS = set("SHDC")


class RecognitionCategory(Enum):
    STACK = 'stack'
    BET = 'bet'
    POT = 'pot'
    SMALLPOT = 'smallpot'
    NAMES = 'names'
    HAND = 'hand'
    SUITS = 'suits'
    RANKS = 'ranks'


class CharacterRecognizer:
    def __init__(self, template_path):
        self.base_path = Path(template_path)
        self.templates: Dict[str, List] = {}   # templates da categoria ATIVA
        self.threshold = 0.8
        # Caches: os templates vivem no disco, mas só precisam ser lidos uma vez.
        self._template_cache: Dict["RecognitionCategory", Dict[str, List]] = {}
        self._roi_cache: Dict[tuple, tuple] = {}

    def load_templates(self, category):
        """Ativa os templates da categoria. So le do disco na primeira vez."""
        if category not in self._template_cache:
            self._template_cache[category] = self._read_templates(category)
        self.templates = self._template_cache[category]

    def recognize_cached(self, category, roi_name, roi: np.ndarray, processor):
        """
        processor(roi), reaproveitando o resultado quando os pixels do ROI sao
        identicos aos do frame anterior. O OCR por template e deterministico:
        mesmos pixels => mesmo texto. Numa mesa parada (a maioria dos frames),
        quase nenhum ROI muda.
        """
        key = (category, roi_name)
        signature = (roi.shape, roi.tobytes())
        hit = self._roi_cache.get(key)
        if hit is not None and hit[0] == signature:
            return hit[1]
        result = processor(roi)
        self._roi_cache[key] = (signature, result)
        return result

    def _read_templates(self, category) -> Dict[str, List]:
        """Le a pasta da categoria; o caractere de cada template vem do nome do arquivo."""
        print(f"Carregando templates para categoria: {category.value}\n")
        template_dir = self.base_path / category.value
        if not template_dir.exists():
            raise ValueError(f"Diretório de templates não encontrado: {template_dir}")

        templates: Dict[str, List] = {}
        for char, paths in discover_templates(template_dir).items():
            loaded = [t for t in map(self._load_template, paths) if t is not None]
            if loaded:
                templates[char] = loaded
        return templates

    def _load_template(self, template_path: Path) -> Optional[np.ndarray]:
        template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
        if template is None:
            print(f"Erro ao carregar template: {template_path}")
            return None
        return template

    def recognize_text_from_roi(self, roi: np.ndarray) -> str:
        img_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        all_matches = []

        for char, template_list in self.templates.items():
            for template in template_list:
                w, h = template.shape[::-1]

                res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)

                locations = np.where(res >= self.threshold)

                for pt in zip(*locations[::-1]):
                    score = res[pt[1], pt[0]]
                    match_info = {
                        'char': char,
                        'point': pt,
                        'score': score,
                        'width': w,
                        'height': h
                    }

                    all_matches.append(match_info)

        all_matches.sort(key=lambda x: x['score'], reverse=True)
        final_characters = []

        for match in all_matches:
            if not self._is_overlapping_with_matches(match, final_characters):
                final_characters.append(match)

        final_characters.sort(key=lambda x: x['point'][0])
        return "".join([char['char'] for char in final_characters])

    def convert_to_float(self, text: str) -> float:
        """Converte um texto reconhecido em float, tolerando "", lixo de OCR
        e virgula decimal. Nunca levanta excecao."""
        num_str = (text or "").strip().replace(',', '.')
        num_str = num_str.replace('..', '.').rstrip('.')
        try:
            return float(num_str) if num_str.replace('.', '', 1).isdigit() else 0.0
        except ValueError:
            return 0.0

    def recognize_number_from_roi(self, roi: np.ndarray) -> float:
        """Reconhece um número a partir da ROI da imagem e o converte para float."""
        text = self.recognize_text_from_roi(roi)
        return self.convert_to_float(text)

    def _is_overlapping_with_matches(self, new_match: dict, existing_matches: list) -> bool:
        new_x, new_y = new_match['point']
        new_w, new_h = new_match['width'], new_match['height']

        new_rect = {
            'left': new_x,
            'right': new_x + new_w,
            'top': new_y,
            'bottom': new_y + new_h
        }

        for existing in existing_matches:
            ex_x, ex_y = existing['point']
            ex_w, ex_h = existing['width'], existing['height']

            exist_rect = {
                'left': ex_x,
                'right': ex_x + ex_w,
                'top': ex_y,
                'bottom': ex_y + ex_h
            }

            if not (new_rect['right'] < exist_rect['left'] or
                    new_rect['left'] > exist_rect['right'] or
                    new_rect['bottom'] < exist_rect['top'] or
                    new_rect['top'] > exist_rect['bottom']):

                overlap_width = min(new_rect['right'], exist_rect['right']) - max(new_rect['left'], exist_rect['left'])
                overlap_height = min(new_rect['bottom'], exist_rect['bottom']) - max(new_rect['top'], exist_rect['top'])
                overlap_area = overlap_width * overlap_height

                min_area = min(new_w * new_h, ex_w * ex_h)
                if overlap_area > 0.25 * min_area:
                    return True

        return False


class TableRecognizer:
    def __init__(self, config: RoomConfig):
        
        self.config = config
        self.char_recognizer = CharacterRecognizer(config.template_path)
        self.player_detector = PlayerDetector(config)

        self.dealer_positions = config.dealer_config.positions
        self.dealer_button_color = config.dealer_config.color_rgb
        self.color_threshold = config.dealer_config.color_threshold
        self.dealer_neighborhood_radius = config.dealer_config.neighborhood_radius
        self.dealer_min_matching_ratio = config.dealer_config.min_matching_ratio

    # ---- Dealer ----

    def detect_dealer_position(self, image: np.ndarray) -> int:
        for position, (x, y) in self.dealer_positions.items():
            pixel_color = image[y, x]
            if np.all(np.abs(pixel_color - self.dealer_button_color) < self.color_threshold):
                return position
        return -1

    def detect_dealer_array_pixel(self, image: np.ndarray) -> int:
        if image is None or image.ndim < 3 or self.dealer_button_color is None:
            return -1

        reference_colors = tuple(reversed(self.dealer_button_color))
        detections = detect_pixels_in_window(
            image,
            self.dealer_positions,
            reference_colors,
            threshold=self.color_threshold,
            window_size=(
                self.dealer_neighborhood_radius * 2 + 1,
                self.dealer_neighborhood_radius * 2 + 1,
            ),
            min_matching_ratio=self.dealer_min_matching_ratio,
        )
        return next((position for position, found in detections.items() if found), -1)

    # ---- Blinds / button ----

    def _assign_button(self, players: List[Player], dealer_position: int) -> None:
        """Marca o BTN no seat do dealer (se presente e sem posicao definida)."""
        seat_to_player = {p.seat: p for p in players}
        dealer = seat_to_player.get(dealer_position)
        if dealer and dealer.is_present and dealer.pos_preflop is None:
            dealer.pos_preflop = Position.BTN

    def _assign_blinds_geometric(self, players: List[Player], dealer_position: int) -> None:
        """
        Fallback quando validate_preflop_bets nao identifica os blinds
        (ex.: apostas ainda nao legiveis no inicio da mao).

        Regra (igual ao antigo BlindsManager.identify_blinds):
          - 3+ jogadores: SB = primeiro seat PRESENTE apos o button (ordem
            crescente de seat, com wrap-around); BB = proximo presente.
          - Heads-up: o proprio button eh o SB; o outro jogador eh o BB.
        """
        if dealer_position < 0 or not players:
            return

        seat_to_player = {p.seat: p for p in players}
        present_seats = sorted(p.seat for p in players if p.is_present)
        if len(present_seats) < 2:
            return

        # Heads-up: button = SB
        if len(present_seats) == 2:
            if dealer_position in present_seats:
                other = next(s for s in present_seats if s != dealer_position)
                seat_to_player[dealer_position].pos_preflop = Position.SB
                seat_to_player[other].pos_preflop = Position.BB
            return

        # 3+ jogadores: percorre seats a partir do button+1, com wrap
        n = max(present_seats) + 1
        sb_seat = None
        bb_seat = None
        for step in range(1, n + 1):
            seat = (dealer_position + step) % n
            if seat not in seat_to_player or not seat_to_player[seat].is_present:
                continue
            if sb_seat is None:
                sb_seat = seat
            else:
                bb_seat = seat
                break

        if sb_seat is not None and bb_seat is not None:
            seat_to_player[sb_seat].pos_preflop = Position.SB
            seat_to_player[bb_seat].pos_preflop = Position.BB

    def _resolve_bb_amount(self) -> float:
        """BB configurado (config.bb_amount). 0.0 se nao configurado."""
        return float(getattr(self.config, 'bb_amount', 0.0) or 0.0)

    # ---- Board ----

    def _parse_board(self, rank_text: str, suit_text: str) -> List[Card]:
        """
        Monta o board a partir dos textos OCR de rank e suit (um caractere
        por carta, na ordem). zip() tolera tamanhos diferentes entre os dois
        textos (o antigo range(len(rank)) levantava IndexError nesse caso).
        Cartas com caractere invalido sao descartadas. Maximo 5 cartas.
        """
        cards: List[Card] = []
        for r, s in zip((rank_text or "").upper(), (suit_text or "").upper()):
            if r in VALID_RANKS and s in VALID_SUITS:
                cards.append(Card(rank=r, suit=s))
            if len(cards) >= 5:
                break
        return cards

    # ---- Pipeline principal ----

    def process_table(
        self,
        image: np.ndarray,
        snapshot_path: Optional[str] = None,
    ) -> TableInfo:
        """
        Processa a imagem da mesa e extrai todas as informacoes.

        Args:
            image: screenshot da mesa como numpy array (BGR).
            snapshot_path: caminho do PNG que originou esta leitura (opcional).

        Returns:
            TableInfo (core.models) com tudo que foi reconhecido.
        """
        players = self.player_detector.detect_players(image)
        roi_config = self.config.roi_config

        # Função auxiliar genérica para processamento de ROIs
        def process_rois(roi_dict, category, processor, attr_name=None):
            if not roi_dict:
                return None

            self.char_recognizer.load_templates(category)

            recognize = self.char_recognizer.recognize_cached

            # Para ROIs de jogador (com posição no nome)
            if attr_name:
                for name, (x, y, w, h) in roi_dict.items():
                    roi = image[y:y+h, x:x+w]
                    result = recognize(category, name, roi, processor)
                    position = int(name.split('_')[1])
                    if position < len(players):
                        setattr(players[position], attr_name, result)
                return None
            # Para ROIs únicos (pot/smallpot)
            else:
                # Processa apenas a primeira ROI (assumindo que há apenas uma)
                name, (x, y, w, h) = next(iter(roi_dict.items()))
                roi = image[y:y+h, x:x+w]
                return recognize(category, name, roi, processor)

        # Preenche stack / current_bet / name nos players
        process_rois(roi_config.stacks, RecognitionCategory.STACK,
                     self.char_recognizer.recognize_number_from_roi, 'stack')

        process_rois(roi_config.bets, RecognitionCategory.BET,
                     self.char_recognizer.recognize_number_from_roi, 'current_bet')

        process_rois(roi_config.names, RecognitionCategory.NAMES,
                     self.char_recognizer.recognize_text_from_roi, 'name')

        # Pot / smallpot / hand id (texto; conversao numerica depois)
        pot_text = process_rois(roi_config.pot, RecognitionCategory.POT,
                                self.char_recognizer.recognize_text_from_roi) or ""

        small_pot_text = process_rois(roi_config.smallpot, RecognitionCategory.SMALLPOT,
                                      self.char_recognizer.recognize_text_from_roi) or ""

        hand_id = process_rois(roi_config.hand, RecognitionCategory.HAND,
                               self.char_recognizer.recognize_text_from_roi) or ""

        # Dealer position
        if self.config.dealer_config.detection_method == DetectionMethod.ARRAY_PIXEL:
            dealer_position = self.detect_dealer_array_pixel(image)
        else:
            dealer_position = self.detect_dealer_position(image)

        # Board (List[Card] validada)
        rank_text = process_rois(roi_config.ranks, RecognitionCategory.RANKS,
                                 self.char_recognizer.recognize_text_from_roi) or ""
        suit_text = process_rois(roi_config.suits, RecognitionCategory.SUITS,
                                 self.char_recognizer.recognize_text_from_roi) or ""
        community_cards = self._parse_board(rank_text, suit_text)

        # Blinds:
        #   1. marca o button (sempre, independente do metodo de blinds);
        #   2. SB/BB por valor apostado (validate_preflop_bets);
        #   3. fallback geometrico pelo button se as apostas nao identificar.
        self._assign_button(players, dealer_position)
        bb_amount = self._resolve_bb_amount()
        bb_positions: List[int] = []
        if bb_amount > 0:
            bb_positions = validate_preflop_bets(players, bb_amount)
        if not bb_positions:
            self._assign_blinds_geometric(players, dealer_position)

        # Create debug image if needed
        if self.config.debug_mode:
            create_debug_image(image, self.config, dealer_position, players,
                               community_cards)

        return TableInfo(
            hand=hand_id,
            pot=self.char_recognizer.convert_to_float(pot_text),
            small_pot=self.char_recognizer.convert_to_float(small_pot_text),
            dealer_position=dealer_position,
            community_cards=community_cards,
            players=players,
            bb_positions=bb_positions,
            sb_amount=(bb_amount / 2) if bb_amount > 0 else 0.0,
            bb_amount=bb_amount,
            snapshot_path=snapshot_path,
        )


class TableAnalyzer:
    """Facade usado pelo PokerRoom (rooms/poker_room.py)."""

    def __init__(self, config: RoomConfig):
        self.table_config = config
        self.table_recognizer = TableRecognizer(config)

    def analyze_table(
        self,
        snapshot: Optional[np.ndarray] = None,
        snapshot_path: Optional[str] = None,
    ) -> TableInfo:
        """
        Retorna o TableInfo produzido pelo recognizer (sem re-conversao --
        o processo inteiro vive no process_table do TableRecognizer).
        """
        if snapshot is None:
            # For testing purposes, load a sample image
            snapshot = cv2.imread(self.table_config.sample_image_path)
            if snapshot is None:
                raise ValueError("No snapshot provided and couldn't load sample image")

        return self.table_recognizer.process_table(snapshot, snapshot_path=snapshot_path)


class PlayerDetector:
    def __init__(self, config: RoomConfig):
        self.absent_template = cv2.imread(config.emptySeatTemplate, cv2.IMREAD_GRAYSCALE)
        self.threshold = config.player_detection_config.threshold
        self.player_positions = config.player_detection_config.positions

    def detect_players(self, image: np.ndarray) -> List[Player]:
        players = []
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        for pos, roi in self.player_positions.items():
            x, y, w, h = roi
            region = gray_image[y:y+h, x:x+w]
            is_present = True
            if self.absent_template is not None:
                result = cv2.matchTemplate(region, self.absent_template, cv2.TM_CCOEFF_NORMED)
                if np.max(result) >= self.threshold:
                    is_present = False
            players.append(Player(
                name='',
                seat=pos,                  # renomeado de 'position' para 'seat'
                stack=0.0,
                current_bet=0.0,
                is_present=is_present,
                # is_active: o recognizer ainda nao le badge de fold, entao
                # usa presenca como proxy (player presente = ativo). Quando
                # o OCR de badges (last_action) existir, marcar fold aqui.
                is_active=is_present,
                # pos_preflop default None; eh preenchido pelo pipeline de
                # blinds no TableRecognizer (BTN/SB/BB).
            ))

        return players
