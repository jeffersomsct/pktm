"""Preparo comum dos testes: raiz do projeto no sys.path e atalhos."""
import contextlib
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))                # os caminhos do projeto nao dependem do diretorio atual

from config.room_config import get_swc_poker_config_v3        # noqa: E402
from core.imageio import read_image                            # noqa: E402
from poker_table_recognizer import TableAnalyzer              # noqa: E402

# Titulo real da janela da amostra v3 (torneio, nivel 20/40 com ante 8).
SAMPLE_TITLE = "Hourly Freeroll - NLH [10 Chips]  -  Level 20/40 ante 8;  Next Level 25/50 ante 10"


def quiet():
    return contextlib.redirect_stdout(io.StringIO())


def load_sample():
    """(config v3, imagem da amostra). A amostra e a unica imagem v3 sem perda do repositorio."""
    config = get_swc_poker_config_v3()
    image = read_image(config.sample_image_path)
    assert image is not None, f"amostra nao encontrada: {config.sample_image_path}"
    return config, image


def analyze(image, title=SAMPLE_TITLE, analyzer=None):
    with quiet():
        return (analyzer or TableAnalyzer(get_swc_poker_config_v3())).analyze_table(image, title=title)


def snapshot(table_info):
    """Tudo o que o reconhecedor produz, em forma comparavel."""
    return (table_info.hand, table_info.pot, table_info.small_pot, table_info.dealer_position,
            tuple(str(c) for c in table_info.community_cards), tuple(table_info.bb_positions),
            (table_info.sb_amount, table_info.bb_amount, table_info.ante),
            tuple((p.seat, p.name, p.stack, p.current_bet, p.is_present, p.is_active,
                   p.pos_preflop.value if p.pos_preflop else None) for p in table_info.players))
