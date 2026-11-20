"""
poker_table_recognizer.py
Reconhecimento visual da mesa (CV): template matching, ROIs, OCR.

process_table(): presença por assento -> stack / aposta / nome só dos assentos ocupados ->
pot, small pot, número da mão -> dealer -> board -> posições (BTN / SB / BB).
"""
import numpy as np
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional, Tuple
import cv2

from config.room_config import DetectionMethod, RoomConfig
from config.pixel_detector import detect_pixels_in_window
from config.templates import discover_templates

from core.imageio import read_image
from core.models import Player, TableInfo, Card
from core.blinds import assign_blinds, parse_blinds
from core.debug_image import create_debug_image


VALID_RANKS = set("23456789TJQKA")
VALID_SUITS = set("SHDC")

# Assento ocupado: todo jogador sentado mostra o stack (ou um rotulo: ALL IN, FAZENDO SIT OUT...)
# em amarelo/dourado, e assento vazio nao tem amarelo. Medido em 3 imagens sem perda (27 assentos,
# torneio e cash) e em 41 quadros reais de uma sessao (369 assentos, tema azul, alguns escurecidos):
# vazios <= 0.005 e ocupados >= 0.048 da area do ROI do stack. O limiar fica no meio, com folga.
SEAT_MIN_YELLOW = 0.02
# Brilho minimo (V do HSV): 45 e nao 80 porque o texto dourado de quem esta em sit out e fosco e,
# com a mesa escurecida, cai abaixo de 80. Com 80, 8% dos assentos ocupados eram dados como vazios.
YELLOW_MIN_VALUE = 45


def _yellow_fraction(roi: np.ndarray) -> float:
    """Fracao de pixels amarelo/dourado (matiz 12-35, saturados) de um ROI BGR."""
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    return float(((h >= 12) & (h <= 35) & (s >= 100) & (v >= YELLOW_MIN_VALUE)).mean())


def _drop_thousands_dots(text: str) -> str:
    """
    O OCR le a virgula de milhar como '.': '6.153' deve virar '6153'. Um '.' so e decimal quando
    vem no fim com 1 ou 2 digitos ('1.60', '12.92') ou quando a parte inteira e 0 ('0.125').
    Assume no maximo 2 casas decimais fora desse caso (a SwC mostra centavos, nunca 3 casas).
    """
    parts = text.split(".")
    if len(parts) < 2 or parts[0].strip("0") == "":
        return text
    groups = parts[1:]
    if all(len(g) == 3 for g in groups):                                   # 6.153 | 1.234.567
        return "".join(parts)
    if len(groups) >= 2 and all(len(g) == 3 for g in groups[:-1]) and len(groups[-1]) in (1, 2):
        return "".join(parts[:-1]) + "." + parts[-1]                       # 1.234.56 -> 1234.56
    return text


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
        template = read_image(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            print(f"Erro ao carregar template: {template_path}")
            return None
        return template

    def recognize_glyphs(self, roi: np.ndarray) -> List[Tuple[int, str]]:
        """Template matching no ROI: [(x, caractere)] ordenado por x, sem sobreposicao."""
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
        return [(int(c['point'][0]), c['char']) for c in final_characters]

    def recognize_text_from_roi(self, roi: np.ndarray) -> str:
        return "".join(char for _, char in self.recognize_glyphs(roi))

    def convert_to_float(self, text: str) -> float:
        """Converte um texto reconhecido em float, tolerando "", lixo de OCR, virgula decimal
        e separador de milhar lido como '.'. Nunca levanta excecao."""
        num_str = (text or "").strip().replace(',', '.')
        num_str = num_str.replace('..', '.').rstrip('.')
        num_str = _drop_thousands_dots(num_str)
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

        self.dealer_positions = config.dealer_config.positions
        self.dealer_button_color = config.dealer_config.color_rgb
        self.color_threshold = config.dealer_config.color_threshold
        self.dealer_neighborhood_radius = config.dealer_config.neighborhood_radius
        self.dealer_min_matching_ratio = config.dealer_config.min_matching_ratio
        self._size_warned = False

    # ---- Geometria ----

    def _check_size(self, image: np.ndarray) -> None:
        """Os ROIs sao pixel-exatos: com outro tamanho de captura os valores saem errados, em silencio."""
        expected = self.config.expected_size
        if not expected or self._size_warned:
            return
        height, width = image.shape[:2]
        if (width, height) != tuple(expected):
            self._size_warned = True
            print(f"AVISO: captura de {width}x{height}, mas os ROIs de {self.config.room_name} foram "
                  f"calibrados para {expected[0]}x{expected[1]}. Os valores lidos tendem a sair errados.")

    # ---- Jogadores ----

    def _detect_players(self, image: np.ndarray) -> List[Player]:
        """Um Player por assento, com is_present pela cor do stack (ver SEAT_MIN_YELLOW)."""
        players = []
        for name, (x, y, w, h) in self.config.roi_config.stacks.items():
            seat = int(name.split('_')[1])
            present = _yellow_fraction(image[y:y + h, x:x + w]) >= SEAT_MIN_YELLOW
            players.append(Player(
                name='',
                seat=seat,
                stack=0.0,
                current_bet=0.0,
                is_present=present,
                # is_active: o recognizer ainda nao le fold, entao usa presenca como proxy.
                is_active=present,
            ))
        players.sort(key=lambda p: p.seat)
        return players

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

    # ---- Board ----

    def _read_glyphs(self, image: np.ndarray, roi_dict, category) -> List[Tuple[int, str]]:
        """[(x absoluto, caractere)] do (unico) ROI do dicionario."""
        if not roi_dict:
            return []
        self.char_recognizer.load_templates(category)
        name, (x, y, w, h) = next(iter(roi_dict.items()))
        glyphs = self.char_recognizer.recognize_cached(
            category, name, image[y:y + h, x:x + w], self.char_recognizer.recognize_glyphs)
        return [(x + gx, char) for gx, char in glyphs]

    def _parse_board(self, ranks: List[Tuple[int, str]], suits: List[Tuple[int, str]]) -> List[Card]:
        """
        Pareia rank e naipe pela CARTA em que cada glifo cai (fatias de card_pitch px a partir de
        board_left). Parear pela ordem de leitura desalinhava tudo quando um glifo nao era lido
        (um 10 sem template fazia 5s Th Kd virar 5s Kh). Aqui, glifo faltando derruba so aquela carta.
        """
        left, pitch = self.config.roi_config.board_left, self.config.roi_config.card_pitch
        rank_at: Dict[int, str] = {}
        suit_at: Dict[int, str] = {}
        for gx, char in ranks:
            rank_at.setdefault((gx - left) // pitch, char.upper())
        for gx, char in suits:
            suit_at.setdefault((gx - left) // pitch, char.upper())

        cards: List[Card] = []
        for slot in sorted(rank_at.keys() & suit_at.keys()):
            rank, suit = rank_at[slot], suit_at[slot]
            if 0 <= slot < 5 and rank in VALID_RANKS and suit in VALID_SUITS:
                cards.append(Card(rank=rank, suit=suit))
        return cards

    # ---- Pipeline principal ----

    def process_table(
        self,
        image: np.ndarray,
        snapshot_path: Optional[str] = None,
        title: Optional[str] = None,
    ) -> TableInfo:
        """
        Processa a imagem da mesa e extrai todas as informacoes.

        Args:
            image: screenshot da mesa como numpy array (BGR).
            snapshot_path: caminho do PNG que originou esta leitura (opcional).
            title: titulo da janela; dele saem os valores das blinds (ex.: 'Level 40/80 ante 16').

        Returns:
            TableInfo (core.models) com tudo que foi reconhecido.
        """
        self._check_size(image)
        players = self._detect_players(image)
        roi_config = self.config.roi_config

        # Funcao auxiliar generica para processamento de ROIs
        def process_rois(roi_dict, category, processor, attr_name=None):
            if not roi_dict:
                return None

            self.char_recognizer.load_templates(category)

            recognize = self.char_recognizer.recognize_cached

            # ROIs de jogador ('stack_3'): so os assentos ocupados sao lidos (assento vazio
            # so da lixo de OCR e custa tempo).
            if attr_name:
                for name, (x, y, w, h) in roi_dict.items():
                    seat = int(name.split('_')[1])
                    if seat >= len(players) or not players[seat].is_present:
                        continue
                    roi = image[y:y+h, x:x+w]
                    setattr(players[seat], attr_name, recognize(category, name, roi, processor))
                return None
            # ROIs unicos (pot/smallpot/hand)
            else:
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
        ranks = self._read_glyphs(image, roi_config.ranks, RecognitionCategory.RANKS)
        suits = self._read_glyphs(image, roi_config.suits, RecognitionCategory.SUITS)
        community_cards = self._parse_board(ranks, suits)

        # Posicoes (BTN/SB/BB) pela ordem de jogo a partir do dealer; valores das blinds pelo titulo.
        bb_positions = assign_blinds(players, dealer_position, len(roi_config.stacks), self.config.seat_step)
        sb_amount, bb_amount, ante = parse_blinds(title)

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
            sb_amount=sb_amount,
            bb_amount=bb_amount,
            ante=ante,
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
        title: Optional[str] = None,
    ) -> TableInfo:
        """
        Retorna o TableInfo produzido pelo recognizer (sem re-conversao --
        o processo inteiro vive no process_table do TableRecognizer).
        """
        if snapshot is None:
            # For testing purposes, load a sample image
            snapshot = read_image(self.table_config.sample_image_path)
            if snapshot is None:
                raise ValueError("No snapshot provided and couldn't load sample image")

        return self.table_recognizer.process_table(snapshot, snapshot_path=snapshot_path, title=title)
