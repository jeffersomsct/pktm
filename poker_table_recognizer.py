import numpy as np
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from core.blinds_manager import BlindsManager
from config.room_config import RoomConfig
from core.window_handler import search_parent_window
from images.capture import snapshot
import cv2
from codemap import Position
import os
from datetime import datetime
from core.debug_image import create_debug_image



@dataclass
class Player:
    name: str
    position: int
    pos_preflop: Position
    is_present: bool
    is_active: bool
    stack: float
    current_bet: float
    just_joined: bool = False
    pending_big_blind: bool = False


@dataclass
class TableState:
    hand: str
    pot: str
    small_pot: str
    dealer_position: int
    community_cards: List[tuple]
    players: List[Player]



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
    def __init__(self, template_path, template_mapping: Optional[Dict] = None):
        self.base_path = Path(template_path)
        self.templates: Dict[str, List] = {}
        self.target_size = (32, 32)
        self.threshold = 0.8
        # template_mapping can be dict with keys = category.value (strings) or None
        self.template_mapping = template_mapping
        self.mapping_version = 'swc'  # fallback if no mapping dict provided

    def _get_template_mapping_Swc_v1(self, category) -> Dict[str, List[str]]:
        # Fallback vazio: preferir template_mapping vindo da RoomConfig
        return {}

    def _get_template_mapping_Swc_v2(self, category) -> Dict[str, List[str]]:
        # Fallback vazio: preferir template_mapping vindo da RoomConfig
        return {}

    def load_templates(self, category):
        print(f"Carregando templates para categoria: {category.value}\n")
        self.templates.clear()
        template_dir = self.base_path / category.value
        if not template_dir.exists():
            raise ValueError(f"Diretório de templates não encontrado: {template_dir}")

        # If config supplied a mapping dict, prefer it (keys as category.value)
        if isinstance(self.template_mapping, dict):
            template_mapping = self.template_mapping.get(category.value, {})
        else:
            # fallback to original mapping choice
            if self.mapping_version == 'swc_v1':
                template_mapping = self._get_template_mapping_Swc_v1(category)
            else:
                template_mapping = self._get_template_mapping_Swc_v2(category)

        # Verifica se o template_mapping é um dicionário de strings (caminhos simples)
        if template_mapping and isinstance(next(iter(template_mapping.values())), str):
            for char, template_file in template_mapping.items():
                template_path = template_dir / template_file
                if template_path.exists():
                    template = self._load_template(template_path)
                    if template is not None:
                        self.templates[char] = [template]
                else:
                    print(f"Template não encontrado: {template_path}")
        else:
            # Código original para lista de templates
            for char, template_files in template_mapping.items():
                if not isinstance(template_files, (list, tuple)):
                    template_files = [template_files]
                    
                template_list = []
                for template_file in template_files:
                    template_path = template_dir / template_file
                    if template_path.exists():
                        template = self._load_template(template_path)
                        if template is not None:
                            template_list.append(template)
                    else:
                        print(f"Template não encontrado: {template_path}")

                if template_list:
                    self.templates[char] = template_list

    def _load_template(self, template_path: Path) -> Optional[np.ndarray]:
        template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
        if template is None:
            print(f"Erro ao carregar template: {template_path}")
            return None
        return template

    def recognize_text_from_roi(self, roi: np.ndarray) -> str:
        import matplotlib.pyplot as plt

        #plt.imshow(roi)
        #plt.axis('off')  # Remove os eixos
        #plt.show()
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
                    # LOG: salvar a miniatura da região onde a imagem foi encontrada
                    log_dir = "imgs/log/"
                    all_matches.append(match_info)

                    # 🔹 Recortar a região do caractere detectado no ROI
                    x, y = pt
                    char_crop = roi[y:y+h, x:x+w]  # Recorta a região do caractere

                    # 🔹 Nome do arquivo baseado no caractere e coordenadas
                    filename = f"{log_dir}{char}_{x}_{y}.png"
                    # cv2.imwrite(filename, char_crop)  # Salva a imagem
                    img_with_boxes = roi.copy()  # Cria uma cópia para desenhar as marcações
                    # 🔹 Desenhar o retângulo na imagem de marcação
                    #cv2.rectangle(img_with_boxes, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    #cv2.putText(img_with_boxes, char, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    #cv2.imwrite('imgs/log/img_log.png', img_with_boxes)
                   # print()
                    # LOG FIM ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||

        all_matches.sort(key=lambda x: x['score'], reverse=True)
        final_characters = []
        
        for match in all_matches:
            if not self._is_overlapping_with_matches(match, final_characters):
                final_characters.append(match)
        
        final_characters.sort(key=lambda x: x['point'][0])
        return "".join([char['char'] for char in final_characters])


    def convert_to_float(self, text: str) -> float:
        """Converte um texto reconhecido em um número float, lidando com erros."""
        num_str = text.strip().replace(',', '.')  # Caso existam vírgulas como separador decimal

        num_str = text.strip().replace(',', '.')  # Substitui vírgula por ponto  
        num_str = num_str.replace('..', '.')  # Corrige múltiplos pontos seguidos  
        # Substitui '.' isolado por '', e se a string for vazia, assume 0.0
        try:
            return float(num_str) if num_str.replace('.', '', 1).isdigit() else 0.0
        except ValueError:
            return 0.0
        

    def recognize_number_from_roi(self, roi: np.ndarray) -> float:
        """Reconhece um número a partir da ROI da imagem e o converte para float."""
        text = self.recognize_text_from_roi(roi)  # Usa o método de reconhecimento de texto
        return self.convert_to_float(text)  # Converte o resultado para float




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
    


@dataclass
class TableInfo:
    # Estado completo da mesa
    hand: str
    pot: str
    small_pot: str
    dealer_position: int
    community_cards: List[tuple]
    players: List[Player]
    bb_positions: List[int]

    
class TableRecognizer:
    def __init__(self, config: RoomConfig):
        self.config = config
        # passa o mapping dict da config (ou None) para o CharacterRecognizer
        self.char_recognizer = CharacterRecognizer(config.template_path, getattr(config, 'template_mapping', None))
        self.player_detector = PlayerDetector(config)

        self.dealer_positions = config.dealer_config.positions
        self.dealer_button_color = config.dealer_config.color_rgb 
        self.color_threshold = config.dealer_config.color_threshold

        self.blinds_manager = BlindsManager(min_small_blind=1, min_big_blind=2)
        
    def detect_dealer_position(self, image: np.ndarray) -> int:
        for position, (x, y) in self.dealer_positions.items():
            pixel_color = image[y, x]
            if np.all(np.abs(pixel_color - self.dealer_button_color) < self.color_threshold):
                return position
        return -1

    def process_table(self, image: np.ndarray) -> TableState:
        """
        Process the poker table image and extract all relevant information.

        Args:
            image: The table screenshot as a numpy array
            
        Returns:
            TableState object containing all recognized information
        """
        players = self.player_detector.detect_players(image)
        roi_config = self.config.roi_config

        # Função auxiliar genérica para processamento de ROIs
        def process_rois(roi_dict, category, processor, attr_name=None):
            if not roi_dict:
                return None
                
            self.char_recognizer.load_templates(category)
            
            # Para ROIs de jogador (com posição no nome)
            if attr_name:
                for name, (x, y, w, h) in roi_dict.items():
                    roi = image[y:y+h, x:x+w]
                    result = processor(roi)
                    position = int(name.split('_')[1])
                    if position < len(players):
                        setattr(players[position], attr_name, result)
                return None
            # Para ROIs únicos (pot/smallpot)
            else:
                # Processa apenas a primeira ROI (assumindo que há apenas uma)
                x, y, w, h = next(iter(roi_dict.values()))
                roi = image[y:y+h, x:x+w]
                return processor(roi)

        # Processamento simplificado para todas as regiões
        process_rois(roi_config.stacks, RecognitionCategory.STACK, 
                    self.char_recognizer.recognize_number_from_roi, 'stack')

        process_rois(roi_config.bets, RecognitionCategory.BET, 
                    self.char_recognizer.recognize_number_from_roi, 'current_bet')
        
        process_rois(roi_config.names, RecognitionCategory.NAMES, 
                    self.char_recognizer.recognize_text_from_roi, 'name')
        
        # Processamento unificado para pot e smallpot
        pot = process_rois(roi_config.pot, RecognitionCategory.POT, 
                        self.char_recognizer.recognize_text_from_roi) or ""

        small_pot = process_rois(roi_config.smallpot, RecognitionCategory.SMALLPOT, 
                                self.char_recognizer.recognize_text_from_roi) or ""
        hand = process_rois(roi_config.hand, RecognitionCategory.HAND, 
                        self.char_recognizer.recognize_text_from_roi) or ""

        # Detect dealer position
        dealer_position = self.detect_dealer_position(image)

        # Identifica Sb e BB in Players
        players = self.blinds_manager.identify_blinds(players, dealer_position)
        # Identifica as cartas do board
        rank = process_rois(roi_config.ranks, RecognitionCategory.RANKS, 
                                self.char_recognizer.recognize_text_from_roi) or ""
        suit = process_rois(roi_config.suits, RecognitionCategory.SUITS, 
                                self.char_recognizer.recognize_text_from_roi) or ""
        community_cards = []
        for c in range(len(rank)):
            community_cards.append((rank[c], suit[c]))

        # Create debug image if needed
        if self.config.debug_mode:
            create_debug_image(image, self.config, dealer_position, players)
#config: RoomConfig, players: List[Player], image: np.ndarray, player_positions: dict, template_path: str, threshold: float
        players = is_player_present(
            self.config,
            players, 
            image, 
            self.config.player_detection_config.positions,
            self.config.template_path,
            self.config.player_detection_config.threshold
        )

        return TableState(
            community_cards=community_cards,
            hand=hand,
            pot=pot,
            small_pot=small_pot,
            dealer_position=dealer_position,
            players=players
        )


class TableAnalyzer:
    def __init__(self, config: RoomConfig):
        self.table_config = config
        self.blinds_manager = BlindsManager(min_small_blind=1, min_big_blind=2)
        # passar o mapping dict para o CharacterRecognizer
        self.char_recognizer = CharacterRecognizer(config.template_path, getattr(config, 'template_mapping', None))
        self.table_recognizer = TableRecognizer(config)
        self.player_detector = PlayerDetector(config)
        
    def analyze_table(self, snapshot: Optional[np.ndarray] = None) -> TableInfo:
        if snapshot is None:
            # For testing purposes, load a sample image
            snapshot = cv2.imread(self.table_config.sample_image_path)
            if snapshot is None:
                raise ValueError("No snapshot provided and couldn't load sample image")
   
        # Processar a mesa e obter o estado completo
        table_state = self.table_recognizer.process_table(snapshot)
        
        # Validar apostas de big blind
        bb_positions = self.blinds_manager.validate_preflop_bets(table_state.players, bb_amount=2)
        
        # Retornar TableInfo com todas as informações (sem redundância)
        return TableInfo(
            hand=table_state.hand,
            pot=table_state.pot,
            small_pot=table_state.small_pot,
            dealer_position=table_state.dealer_position,
            community_cards=table_state.community_cards,
            players=table_state.players,
            bb_positions=bb_positions
        )



class PlayerDetector:
    def __init__(self, config: RoomConfig):
        self.absent_template = cv2.imread(config.emptySeatTemplate, cv2.IMREAD_GRAYSCALE)
        self.threshold = config.player_detection_config.threshold
        self.player_positions = config.player_detection_config.positions

    def detect_players(self, image: np.ndarray) -> List[Player]:
        players = []
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = os.path.join('imgs/log', f"gray_image_{timestamp}.png")
        # cv2.imwrite(filename, gray_image)
        
        for pos, roi in self.player_positions.items():
            x, y, w, h = roi #room_config.py player_detection_config
            region = gray_image[y:y+h, x:x+w]
            
            is_present = True
            if self.absent_template is not None:
                result = cv2.matchTemplate(region, self.absent_template, cv2.TM_CCOEFF_NORMED)
                if np.max(result) >= self.threshold:
                    is_present = False
  
            players.append(Player(
                is_active= False,
                name = '',
                position=pos,
                pos_preflop='',
                is_present=is_present,
                stack=0.0,
                current_bet=0.0
            ))

        return players

def is_player_present(config: RoomConfig, players: List[Player], image: np.ndarray, player_positions: dict, template_path: str, threshold: float) -> List[Player]:
    """
    Detecta se o player está presente na mesa usando template de assento vazio.
    """
    absent_template = cv2.imread(f"{config.template_path}/others/assento_vazio.png", cv2.IMREAD_GRAYSCALE)
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    for player in players:
        pos = player.position
        if pos in player_positions:
            x, y, w, h = player_positions[pos]
            region = gray_image[y:y+h, x:x+w]
            
            is_present = True
            if absent_template is not None:
                result = cv2.matchTemplate(region, absent_template, cv2.TM_CCOEFF_NORMED)
                if np.max(result) >= threshold:
                    is_present = False
            
            player.is_present = is_present

    return players
