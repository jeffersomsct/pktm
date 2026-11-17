# room_config.py
from dataclasses import dataclass
from typing import ClassVar, Dict, List, Tuple, Optional
from enum import Enum

class DetectionMethod(Enum):
    PIXEL_COLOR = "pixel_color"
    ARRAY_PIXEL = "array_pixel"
    TEMPLATE_MATCHING = "template_matching"
    OCR = "ocr"

@dataclass
class DealerConfig:
    """
    Usa apenas a cor de 1 pixel, definido em color_rgb
    """
    detection_method: DetectionMethod
    positions: Dict[int, Tuple[int, int]]  # Position number -> (x, y)
    color_rgb: Optional[Tuple[int, int, int]] = None  # For pixel color
    color_threshold: Optional[int] = None  # For pixel color
    neighborhood_radius: int = 2
    min_matching_ratio: float = 0.6

@dataclass
class ROIConfig:
    stacks: Dict[str, Tuple[int, int, int, int]]  # name -> (x, y, w, h)
    bets: Dict[str, Tuple[int, int, int, int]]
    names: Dict[str, Tuple[int, int, int, int]]
    pot: Dict[str, Tuple[int, int, int, int]]
    smallpot: Dict[str, Tuple[int, int, int, int]]
    money_exists: Dict[bool, Tuple[bool, bool, bool, bool]]
    hand: Dict[str, Tuple[int, int, int, int]]
    ranks: Dict[str, Tuple[int, int, int, int]]
    suits: Dict[str, Tuple[int, int, int, int]]


@dataclass
class PlayerDetectionConfig:
    detection_method: DetectionMethod
    positions: Dict[int, List[int]]  # Position number -> [x, y, w, h]
    threshold: float = 0.8

@dataclass
class RoomConfig:
    debug_mode: ClassVar[bool] = False
    room_id: str
    room_name: str
    emptySeatTemplate: str
    dealer_config: DealerConfig
    roi_config: ROIConfig
    player_detection_config: PlayerDetectionConfig
    template_path: Optional[str] = None
    sample_image_path:  Optional[str] = None
    big_blind: Optional[float] = 0.04
    

# rooms/swc_poker.py
def get_swc_poker_config() -> RoomConfig:
    template_path = "imgs/models/swc/v1"

    return RoomConfig(
        room_id="swc_poker",
        room_name="SwC Poker",
        template_path=template_path,
        sample_image_path=template_path + "/table_example.png",
        emptySeatTemplate=template_path + "/others/assento_vazio.png",
        dealer_config=DealerConfig(
            detection_method=DetectionMethod.PIXEL_COLOR,
            positions={0: (350, 416), 1: (663, 387), 2: (626, 296), 3: (617, 207),
                       4: (506, 154), 5: (302, 154), 6: (194, 207), 7: (179, 301), 8: (148, 387)},
            color_rgb=(224, 216, 195),
            color_threshold=30
        ),
        roi_config=ROIConfig(
            stacks={ "stack_0": [390, 470, 109, 16], "stack_1": [514, 441, 109, 16], "stack_2": [642, 348, 109, 16],
                     "stack_3": [642, 244, 109, 16], "stack_4": [537, 139, 109, 16], "stack_5": [182, 139, 109, 16],
                     "stack_6": [77, 244, 109, 16], "stack_7": [78, 348, 108, 16], "stack_8": [205, 441, 109, 16] },
            bets={ "bet_0": [433, 370, 61, 30], "bet_1": [481, 339, 61, 30], "bet_2": [530, 308, 61, 30],
                   "bet_3": [578, 256, 61, 30], "bet_4": [531, 190, 61, 30], "bet_5": [230, 190, 61, 30],
                   "bet_6": [190, 256, 61, 30], "bet_7": [221, 308, 61, 30], "bet_8": [266, 339, 61, 30] },
            names={ "name_0": [390, 450, 109, 15], "name_1": [514, 421, 109, 15], "name_2": [642, 328, 109, 15],
                    "name_3": [642, 224, 109, 15], "name_4": [537, 118, 109, 15], "name_5": [182, 118, 109, 15],
                    "name_6": [77, 224, 109, 15], "name_7": [78, 328, 108, 15], "name_8": [205, 421, 109, 15] },
            pot={"pot": [360, 200, 110, 13]},
            smallpot={"smallpot": [355, 325, 118, 17]},
            money_exists={"player_7": [158, 119, 13]},
        ),
        player_detection_config=PlayerDetectionConfig(
            detection_method=DetectionMethod.TEMPLATE_MATCHING,
            positions={0: [396, 471, 35, 12], 1: [589, 441, 35, 12], 2: [717, 349, 35, 12],
                       3: [717, 245, 35, 12], 4: [612, 140, 35, 12], 5: [179, 140, 35, 12],
                       6: [74, 245, 35, 12], 7: [74, 349, 35, 12], 8: [202, 441, 35, 12]},
            threshold=0.8
        )
    )

def get_swc_poker_config_v2() -> RoomConfig:
    template_path = "imgs/models/swc/v2"

    return RoomConfig(
        room_id="swc_poker",
        room_name="SwC Poker",
        template_path=template_path,
        sample_image_path=template_path + "/table_example.png",
        emptySeatTemplate=template_path + "/others/assento_vazio.png",
        dealer_config=DealerConfig(
            detection_method=DetectionMethod.PIXEL_COLOR,
            positions={0: (379, 344), 1: (517, 385), 2: (671, 335), 3: (666, 190),
                       4: (508, 126), 5: (311, 126), 6: (155, 190), 7: (136, 336), 8: (306, 336)},
            color_rgb=(0, 0, 0),
            color_threshold=30
        ),
        roi_config=ROIConfig(
            stacks={ "stack_0": [360, 472, 108, 15], "stack_1": [547, 427, 108, 15], "stack_2": [692, 347, 108, 15],
                     "stack_3": [688, 198, 108, 15], "stack_4": [547, 117, 108, 15], "stack_5": [182, 117, 108, 15],
                     "stack_6": [39, 190, 108, 15], "stack_7": [15, 334, 108, 15], "stack_8": [175, 427, 108, 15] },
            bets={ "bet_0": [430, 347, 63, 33], "bet_1": [514, 330, 63, 33], "bet_2": [623, 278, 63,33],
                   "bet_3": [610, 201, 63, 33], "bet_4": [509, 171, 63, 33], "bet_5": [252, 172, 63, 33],
                   "bet_6": [159, 201, 63, 33], "bet_7": [135, 282, 63, 33], "bet_8": [248, 310, 63, 33] },
            names={ 
                    "name_0": [362, 450, 103, 15], 
                    "name_1": [548, 405, 103, 15], 
                    "name_2": [694, 324, 103, 15],
                    "name_3": [690, 176, 103, 15], 
                    "name_4": [549, 95, 103, 15], 
                    "name_5": [184, 95, 103, 15],
                    "name_6": [41, 168, 103, 15], 
                    "name_7": [17, 312, 103, 15], 
                    "name_8": [176, 405, 103, 15] 
                    },
            pot={"pot": [362, 168, 102, 13]},
            smallpot={"smallpot": [362, 310, 102, 21]},
            money_exists={"player_7": [158, 119, 13]},
            hand={"hand": [733, 30, 91, 11]},
            ranks={"rank": [256, 209, 279, 23]},
            suits={"suit": [256, 234, 279, 13]},
            #ranks={"rank_1": [256, 209, 11, 23], "rank_2": [323, 209, 11, 23],"rank_3": [390, 209, 11, 23],"rank_4": [457, 209, 11, 23],"rank_5": [524, 209, 11, 23]},
            #suits={"suit_1": [256, 234, 11, 13], "suit_2": [323, 234, 11, 13],"suit_3": [390, 234, 11, 13],"suit_4": [457, 234, 11, 13],"suit_5": [524, 234, 11, 13]},
        ),
        player_detection_config=PlayerDetectionConfig(
            detection_method=DetectionMethod.TEMPLATE_MATCHING,
            positions={0: [396, 471, 35, 12], 1: [589, 441, 35, 12], 2: [717, 349, 35, 12],
                       3: [717, 245, 35, 12], 4: [612, 140, 35, 12], 5: [179, 140, 35, 12],
                       6: [74, 245, 35, 12], 7: [74, 349, 35, 12], 8: [202, 441, 35, 12]},
            threshold=0.8
        )
    )

def get_swc_poker_config_v3() -> RoomConfig:
    template_path = "imgs/models/swc/v3"

    return RoomConfig(
        room_id="swc_poker",
        room_name="SwC Poker",
        template_path=template_path,
        sample_image_path=template_path + "/table_example.png",
        emptySeatTemplate=template_path + "/others/assento_vazio.png",
        dealer_config=DealerConfig(
            detection_method=DetectionMethod.PIXEL_COLOR,
            positions={0: (380, 392), 1: (0, 0), 2: (672, 366), 3: (667, 221),
                       4: (615, 181), 5: (210, 181), 6: (156, 221), 7: (137, 367), 8: (307, 367)},
            color_rgb=(0, 0, 0),
            color_threshold=30
        ),
        roi_config=ROIConfig(
            stacks={ "stack_0": [360, 520, 108, 15], "stack_1": [547, 459, 108, 15], "stack_2": [692, 379, 108, 15],
                     "stack_3": [688, 230, 108, 15], "stack_4": [547, 149, 108, 15], "stack_5": [182, 149, 108, 15],
                     "stack_6": [39, 222, 108, 15], "stack_7": [15, 366, 108, 15], "stack_8": [175, 459, 108, 15] },
            bets={ "bet_0": [430, 347, 63, 33], "bet_1": [514, 330, 63, 33], "bet_2": [623, 278, 63,33],
                   "bet_3": [610, 201, 63, 33], "bet_4": [509, 171, 63, 33], "bet_5": [252, 172, 63, 33],
                   "bet_6": [159, 201, 63, 33], "bet_7": [135, 282, 63, 33], "bet_8": [248, 310, 63, 33] },
            names={ 
                    "name_0": [362, 497, 103, 15], 
                    "name_1": [548, 405, 103, 15], 
                    "name_2": [694, 356, 103, 15],
                    "name_3": [690, 207, 103, 15], 
                    "name_4": [549, 126, 103, 15], 
                    "name_5": [184, 126, 103, 15],
                    "name_6": [41, 199, 103, 15], 
                    "name_7": [17, 312, 103, 15], 
                    "name_8": [176, 436, 103, 15] 
                    },
            pot={"pot": [362, 188, 102, 13]},
            smallpot={"smallpot": [362, 338, 102, 21]},
            money_exists={"player_7": [158, 119, 13]},
            hand={"hand": [733, 62, 91, 11]},
            ranks={"rank": [256, 209, 279, 23]},
            suits={"suit": [256, 234, 279, 13]},
            #ranks={"rank_1": [256, 209, 11, 23], "rank_2": [323, 209, 11, 23],"rank_3": [390, 209, 11, 23],"rank_4": [457, 209, 11, 23],"rank_5": [524, 209, 11, 23]},
            #suits={"suit_1": [256, 234, 11, 13], "suit_2": [323, 234, 11, 13],"suit_3": [390, 234, 11, 13],"suit_4": [457, 234, 11, 13],"suit_5": [524, 234, 11, 13]},
        ),
        player_detection_config=PlayerDetectionConfig(
            detection_method=DetectionMethod.TEMPLATE_MATCHING,
            positions={0: [396, 471, 35, 12], 1: [589, 441, 35, 12], 2: [717, 349, 35, 12],
                       3: [717, 245, 35, 12], 4: [612, 140, 35, 12], 5: [179, 140, 35, 12],
                       6: [74, 245, 35, 12], 7: [74, 349, 35, 12], 8: [202, 441, 35, 12]},
            threshold=0.8
        )
    )

# rooms/bodog_poker.py
def get_bodog_poker_config() -> RoomConfig:
    return RoomConfig(
        room_id="bodog_poker",
        room_name="Bodog Poker",
        template_path="imgs/models/others/OPEN.png",
        dealer_config=DealerConfig(
            detection_method=DetectionMethod.PIXEL_COLOR,
            positions={
                0: (350, 416),
                1: (663, 387),
                2: (626, 296),
                3: (617, 207),
                4: (506, 154),
                5: (302, 154),
                6: (194, 207),
                7: (179, 301),
                8: (148, 387),
            },
            color_rgb=(224, 216, 195),  # RGB format
            color_threshold=20
        ),
        roi_config=ROIConfig(
            stacks={
                "stack_0": [390, 470, 110, 16],
                "stack_1": [514, 441, 110, 16],
                "stack_2": [642, 348, 110, 16],
                "stack_3": [642, 244, 110, 16],
                "stack_4": [537, 139, 110, 16],
                "stack_5": [182, 139, 110, 16],
                "stack_6": [77, 244, 110, 16],
                "stack_7": [79, 348, 110, 16],
                "stack_8": [205, 441, 110, 16],
            },
            bets={
                "bet_0": [433, 370, 61, 30],
                "bet_1": [481, 339, 61, 30],
                "bet_2": [530, 308, 61, 30],
                "bet_3": [578, 256, 61, 30],
                "bet_4": [531, 190, 61, 30],
                "bet_5": [200, 190, 61, 30],
                "bet_6": [190, 256, 61, 30],
                "bet_7": [221, 308, 61, 30],
                "bet_8": [266, 339, 61, 30],
            },
            names={
                "name_0": [390, 450, 109, 15],
                "name_1": [514, 421, 109, 15],
                "name_2": [642, 328, 109, 15],
                "name_3": [642, 224, 109, 15],
                "name_4": [537, 118, 109, 15],
                "name_5": [182, 118, 109, 15],
                "name_6": [77, 224, 109, 15],
                "name_7": [79, 328, 109, 15],
                "name_8": [205, 421, 109, 15],
            },
            pot={
                "pot": [360, 200, 110, 13],
            },
            smallpot={
                "smallpot": [355, 325, 118, 17],
            }
        ),
        player_detection_config=PlayerDetectionConfig(
            detection_method=DetectionMethod.TEMPLATE_MATCHING,
            positions={
                0: [396, 471, 35, 12],
                1: [589, 441, 35, 12],
                2: [717, 349, 35, 12],
                3: [717, 245, 35, 12],
                4: [612, 140, 35, 12],
                5: [179, 140, 35, 12],
                6: [74, 245, 35, 12],
                7: [74, 349, 35, 12],
                8: [202, 441, 35, 12]
            },

            threshold=0.8
        )
    )


def get_CoinPoker_config() -> RoomConfig:
    return RoomConfig(
        room_id="coinpoker",
        room_name="CoinPoker",
        emptySeatTemplate="imgs/models/coinpoker/others/assento_vazio.png",
        template_path="imgs/models/coinpoker/",
        sample_image_path="imgs/models/coinpoker/table_example.png",
        dealer_config=DealerConfig(
            detection_method=DetectionMethod.ARRAY_PIXEL,
            positions={
                0: (334, 439), # color_rgb=(243, 242, 243), color_rgb=(245, 244, 244)
                1: (536, 449),
                2: (648, 344),
                3: (547, 160),
                4: (245, 160), # color_rgb=(245, 249, 247)
                5: (144, 344),
                6: (256, 449),
                #7: (179, 301),
                #8: (148, 387),
            },
            color_rgb=(243, 242, 243),  # RGB format
            color_threshold=30,
            neighborhood_radius=2,
            min_matching_ratio=0.60
        ),
        roi_config=ROIConfig(
            stacks={
                "stack_0": [390, 470, 110, 16],
                "stack_1": [514, 441, 110, 16],
                "stack_2": [642, 348, 110, 16],
                "stack_3": [642, 244, 110, 16],
                "stack_4": [537, 139, 110, 16],
                "stack_5": [182, 139, 110, 16],
                "stack_6": [77, 244, 110, 16],
                "stack_7": [79, 348, 110, 16],
                "stack_8": [205, 441, 110, 16],
            },
            bets={
                "bet_0": [433, 370, 61, 30],
                "bet_1": [481, 339, 61, 30],
                "bet_2": [530, 308, 61, 30],
                "bet_3": [578, 256, 61, 30],
                "bet_4": [531, 190, 61, 30],
                "bet_5": [230, 190, 61, 30],
                "bet_6": [190, 256, 61, 30],
                "bet_7": [221, 308, 61, 30],
                "bet_8": [266, 339, 61, 30],
            },
            names={
                "name_0": [390, 450, 109, 15],
                "name_1": [514, 421, 109, 15],
                "name_2": [642, 328, 109, 15],
                "name_3": [642, 224, 109, 15],
                "name_4": [537, 118, 109, 15],
                "name_5": [182, 118, 109, 15],
                "name_6": [77, 224, 109, 15],
                "name_7": [79, 328, 109, 15],
                "name_8": [205, 421, 109, 15],
            },
            pot={
                "pot": [360, 200, 110, 13],
            },
            smallpot={
                "smallpot": [355, 325, 118, 17],
            },
            money_exists={
                True: [True, True, True, True, True, True, True, True, True],
            },
            hand={},
            ranks={},
            suits={}
        ),
        player_detection_config=PlayerDetectionConfig(
            detection_method=DetectionMethod.TEMPLATE_MATCHING,
            positions={
                0: [396, 471, 35, 12],
                1: [589, 441, 35, 12],
                2: [717, 349, 35, 12],
                3: [717, 245, 35, 12],
                4: [612, 140, 35, 12],
                5: [179, 140, 35, 12],
                6: [74, 245, 35, 12],
                7: [74, 349, 35, 12],
                8: [202, 441, 35, 12]
            },
            threshold=0.8
        )
    )