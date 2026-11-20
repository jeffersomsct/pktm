# config/room_config.py
"""
Configuração de salas. Hoje só a SwC, layout v3: janela de 827x601 COM barra de título.

Todos os ROIs são pixel-exatos para ESSA geometria (o reconhecedor avisa se a captura
tiver outro tamanho). Proveniência dos números, quando não vieram da calibração original:

  medido   = conferido em imagens reais da geometria v3 (a amostra table_example.png e
             quadros da gravação de uma sessão de torneio);
  derivado = calculado a partir de ROIs vizinhos ou do espelhamento da mesa. NÃO conferido
             com uma imagem real: ative debug_mode e olhe o debug_table_recognition.png.
"""
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, Dict, Optional, Tuple

from paths import ROOT


class DetectionMethod(Enum):
    PIXEL_COLOR = "pixel_color"
    ARRAY_PIXEL = "array_pixel"


@dataclass
class DealerConfig:
    """Posição (x, y) onde o botão do dealer aparece para cada assento, e a cor a procurar."""
    detection_method: DetectionMethod
    positions: Dict[int, Tuple[int, int]]  # assento -> (x, y)
    color_rgb: Optional[Tuple[int, int, int]] = None
    color_threshold: Optional[int] = None
    neighborhood_radius: int = 2
    min_matching_ratio: float = 0.6


@dataclass
class ROIConfig:
    stacks: Dict[str, Tuple[int, int, int, int]]  # nome -> (x, y, w, h)
    bets: Dict[str, Tuple[int, int, int, int]]
    names: Dict[str, Tuple[int, int, int, int]]
    pot: Dict[str, Tuple[int, int, int, int]]
    smallpot: Dict[str, Tuple[int, int, int, int]]
    hand: Dict[str, Tuple[int, int, int, int]]
    ranks: Dict[str, Tuple[int, int, int, int]]
    suits: Dict[str, Tuple[int, int, int, int]]
    # Board: cada carta ocupa uma "fatia" de card_pitch px a partir de board_left. Rank e naipe
    # são pareados pela fatia em que caem, então um glifo não lido não desalinha as outras cartas.
    board_left: int = 0
    card_pitch: int = 67


@dataclass
class RoomConfig:
    debug_mode: ClassVar[bool] = False
    room_id: str
    room_name: str
    dealer_config: DealerConfig
    roi_config: ROIConfig
    template_path: Optional[str] = None
    sample_image_path: Optional[str] = None
    # (largura, altura) da captura para a qual os ROIs foram calibrados.
    expected_size: Optional[Tuple[int, int]] = None
    # Sentido do jogo em índices de assento. Na SwC os assentos são numerados no sentido
    # anti-horário da tela (0 = herói, embaixo) e a ação anda no sentido horário: -1.
    seat_step: int = -1


def get_swc_poker_config_v3() -> RoomConfig:
    template_path = str(ROOT / "imgs" / "models" / "swc" / "v3")

    return RoomConfig(
        room_id="swc_poker",
        room_name="SwC Poker",
        template_path=template_path,
        sample_image_path=str(ROOT / "imgs" / "models" / "swc" / "v3" / "table_example.png"),
        expected_size=(827, 601),
        seat_step=-1,
        dealer_config=DealerConfig(
            detection_method=DetectionMethod.PIXEL_COLOR,
            # assento 1: derivado do v2 (517, 385) + o mesmo deslocamento (+1, +31) dos assentos 2, 3, 6, 7, 8.
            positions={0: (380, 392), 1: (518, 416), 2: (672, 366), 3: (667, 221),
                       4: (615, 181), 5: (210, 181), 6: (156, 221), 7: (137, 367), 8: (307, 367)},
            color_rgb=(0, 0, 0),
            color_threshold=30,
        ),
        roi_config=ROIConfig(
            stacks={"stack_0": [360, 520, 108, 15], "stack_1": [547, 459, 108, 15], "stack_2": [692, 379, 108, 15],
                    "stack_3": [688, 230, 108, 15], "stack_4": [547, 149, 108, 15], "stack_5": [182, 149, 108, 15],
                    "stack_6": [39, 222, 108, 15], "stack_7": [15, 366, 108, 15], "stack_8": [175, 459, 108, 15]},
            # Apostas: ROIs de 80 px de largura centrados no texto da aposta (o texto e centrado sob as
            # fichas e cresce para os dois lados). Centro do texto em cada assento:
            #   0 (469,411)  2 (652,324)  3 (639,243)  4 (522,187)  5 (321,189)  6 (193,248)  -> MEDIDO
            #   1 (544,375)  7 (186,324)  8 (294,375)  -> DERIVADO (v2 + deslocamento / espelho do 2 e do 1)
            # Medidos: 21 px de altura (o texto tem ~10); isso deixa de fora o icone de fichas, que fica
            # logo acima. Derivados: 34 px, para tolerar o erro da estimativa.
            # bet_0 e mais estreito (64 px): o canto esquerdo do ROI largo pegava o topo do avatar do heroi.
            bets={"bet_0": [437, 401, 64, 21], "bet_1": [504, 358, 80, 34], "bet_2": [612, 314, 80, 21],
                  "bet_3": [599, 233, 80, 21], "bet_4": [482, 177, 80, 21], "bet_5": [281, 179, 80, 21],
                  "bet_6": [153, 238, 80, 21], "bet_7": [146, 307, 80, 34], "bet_8": [254, 358, 80, 34]},
            # name = stack + (2, -23, -5, 0) em todos os assentos medidos; 1 e 7 seguem a mesma relação.
            names={"name_0": [362, 497, 103, 15],
                   "name_1": [549, 436, 103, 15],
                   "name_2": [694, 356, 103, 15],
                   "name_3": [690, 207, 103, 15],
                   "name_4": [549, 126, 103, 15],
                   "name_5": [184, 126, 103, 15],
                   "name_6": [41, 199, 103, 15],
                   "name_7": [17, 343, 103, 15],
                   "name_8": [176, 436, 103, 15]},
            pot={"pot": [362, 188, 102, 13]},
            smallpot={"smallpot": [362, 338, 102, 21]},
            hand={"hand": [733, 62, 91, 11]},
            # Board (medido numa mão real): cartas 60x84 com o canto em (251+67k, 227); rank 11x23 em
            # (258+67k, 232); naipe 11x13 em (258+67k, 257). Os ROIs antigos eram os do v2 e terminavam
            # onde o glifo começa, então o board nunca era lido.
            ranks={"rank": [254, 230, 287, 26]},
            suits={"suit": [254, 255, 287, 17]},
            board_left=251,
            card_pitch=67,
        ),
    )
