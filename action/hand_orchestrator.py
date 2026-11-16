"""
action/hand_orchestrator.py
Orquestra o estado de uma mao ao longo do tempo.

Substitui o antigo poker_hand_state.py. Diferencas:
  - Nao recalcula posicoes (isso eh responsabilidade do Recognizer).
  - Detecta mao nova via mudanca de hand_id e abre/fecha HandRecord.
  - Anexa Actions a street atual em ordem.
  - Tags de captura (motivo do snapshot):
        * preflop_start    -- mao nova, blinds postados
        * street_transition -- flop/turn/river apareceu
        * hero_turn        -- mesa pausada esperando o hero
        * showdown         -- fim da mao, cartas reveladas
        * raw              -- snapshot neutro (polling)
  - process_auto() deriva a tag automaticamente comparando
    TableInfo atual com o estado anterior da sessao.
"""
import time
from typing import List, Optional, Tuple

from core.models import (
    HandRecord, StreetRecord, Action, ActionType, Street, Card,
    TableInfo, TableSession, Player,
    POSITION_ORDER_PREFLOP, POSITION_ORDER_POSTFLOP,
)


VALID_TAGS = {"preflop_start", "street_transition", "hero_turn", "showdown", "raw"}


# ============================================================
# Auto-resolucao de tag (derivada do diff entre observado e armazenado)
# ============================================================

def auto_resolve_tag(table_info: TableInfo, session: TableSession) -> str:
    """
    Determina a tag comparando o TableInfo observado com o estado da sessao.

    A street em si NUNCA eh determinada por comparacao -- eh so contagem de
    cartas em _street_from_board (0=Preflop, 3=Flop, 4=Turn, 5=River).
    A tag so existe pra:
      - nomear o snapshot no disco (raw, hero_turn, etc.)
      - acionar logica especifica do showdown

    Ordem de prioridade (primeiro que bate vence):
      1. preflop_start -- hand_id mudou (ou sessao sem mao ainda)
      2. showdown      -- alguem mostrou cartas OU winners disponivel
      3. hero_turn     -- table_info.hero.is_turn == True
      4. raw           -- caso comum (polling, nada especial)

    Nota: a criacao de StreetRecord quando o flop/turn/river aparece eh
    automatica no process(), via `if street not in hand.streets`.
    Nao precisa de tag pra isso.

    Dependencias do recognizer (para auto-deteccao funcionar):
      - hero.is_turn       -> reconhecer botoes Fold/Call/Raise visiveis
      - player.shown_cards -> reconhecer cartas reveladas no showdown
    """
    # 1. Mao nova?
    if not table_info.hand:
        return "raw"
    if session.last_hand_id is None or table_info.hand != session.last_hand_id:
        return "preflop_start"

    # 2. Showdown? Alguem com shown_cards, OU campo winners populado.
    if any(p.shown_cards for p in table_info.players):
        return "showdown"
    winners = getattr(table_info, "winners", None)
    if winners:
        return "showdown"

    # 3. Hero turn? (requer recognizer populando HeroInfo.is_turn)
    if table_info.hero and table_info.hero.is_turn:
        return "hero_turn"

    # 4. Nada especial.
    return "raw"


def _street_from_board(board: List[Card]) -> Street:
    if not board:
        return Street.PREFLOP
    n = len(board)
    if n == 3:
        return Street.FLOP
    if n == 4:
        return Street.TURN
    if n >= 5:
        return Street.RIVER
    return Street.PREFLOP


# ============================================================
# Orchestrator
# ============================================================

class HandOrchestrator:
    """
    Mantem o HandRecord atual sincronizado com a TableSession.

    Uso tipico (auto-tag, recomendado pra loop de polling):
        orch = HandOrchestrator(session)
        hand, tag = orch.process_auto(table_info)
        # session.current_hand atualizado; 'tag' eh so informativo.

    Uso manual (quando o caller sabe o contexto, ex.: debugging):
        hand = orch.process(table_info, tag="hero_turn")
    """

    def __init__(self, session: TableSession):
        self.session = session
        self.last_tag: Optional[str] = None  # ultima tag resolvida

    def process_auto(
        self,
        table_info: TableInfo,
    ) -> Tuple[Optional[HandRecord], str]:
        """
        Deriva a tag automaticamente e processa.

        Returns:
            (HandRecord ou None, tag usada).
        """
        tag = auto_resolve_tag(table_info, self.session)
        hand = self.process(table_info, tag=tag)
        self.last_tag = tag
        return hand, tag

    def process(
        self,
        table_info: TableInfo,
        tag: str = "raw",
    ) -> Optional[HandRecord]:
        """
        Processa uma nova observacao (TableInfo) e atualiza a TableSession.

        Args:
            table_info: estado bruto da mesa.
            tag: motivo da captura. Um de:
                'preflop_start', 'street_transition', 'hero_turn',
                'showdown', 'raw'.

        Returns:
            HandRecord atual, ou None se hand_id estiver vazio.
        """
        if tag not in VALID_TAGS:
            raise ValueError(
                f"tag invalida: {tag}. Validos: {VALID_TAGS}"
            )
        if not table_info.hand:
            return None

        # 1. Mao nova? (hand_id mudou)
        if table_info.hand != self.session.last_hand_id:
            self._close_current_hand()
            self._start_new_hand(table_info)

        hand = self.session.current_hand
        if hand is None:
            return None

        # 2. Detectar street atual
        street = _street_from_board(table_info.community_cards)

        # 3. Garantir StreetRecord (cria com board_before correto)
        if street not in hand.streets:
            hand.streets[street] = self._make_street_record(street, table_info)

        # 4. Snapshot path (se vier do TableInfo)
        if (table_info.snapshot_path
                and table_info.snapshot_path not in hand.snapshot_paths):
            hand.snapshot_paths.append(table_info.snapshot_path)

        # 5. Extrair acoes visiveis (badges de last_action dos players).
        #    Sempre que houver last_action em algum player, anexar a street.
        #    Extracao eh idempotente (pula players ja registrados), entao
        #    chamar toda iteracao de polling eh seguro.
        self._extract_actions_from_badges(hand, table_info, street)

        # 6. Atualizar pot_after da street
        hand.streets[street].pot_after = table_info.pot

        # 7. Atualiza pots do hand record (main + side)
        if table_info.pots:
            hand.pots = list(table_info.pots)

        # 8. Showdown: cartas mostradas + vencedores
        if tag == "showdown":
            self._process_showdown(hand, table_info)

        # 9. Atualizar fingerprint da TableSession
        self.session.last_seen_at = time.time()
        self.session.last_player_names = [
            p.name for p in table_info.players if p.is_present
        ]

        return hand

    # ---- Helpers internos ----

    def _make_street_record(
        self, street: Street, table_info: TableInfo
    ) -> StreetRecord:
        """
        Cria StreetRecord. board_before = cartas visiveis no inicio da street.
          PREFLOP -> []
          FLOP    -> as 3 do flop
          TURN    -> as 4 (flop+turn)
          RIVER   -> as 5 (flop+turn+river)
        """
        return StreetRecord(
            street=street,
            board_before=list(table_info.community_cards),
            pot_before=table_info.pot,
        )

    def _start_new_hand(self, table_info: TableInfo) -> None:
        hand = HandRecord(
            hand_id=table_info.hand,
            table_id=self.session.table_id,
            tournament_id=(
                table_info.tournament.tournament_id
                if table_info.tournament else None
            ),
            sb_amount=table_info.sb_amount,
            bb_amount=table_info.bb_amount,
            ante=table_info.ante,
            dealer_seat=table_info.dealer_position,
        )

        # Hero info (se o hero estiver na mesa)
        hero_player = next((p for p in table_info.players if p.is_hero), None)
        if hero_player:
            hand.hero_seat = hero_player.seat
            hand.hero_cards = list(hero_player.hole_cards)

        # Street inicial (PREFLOP) -- board_before vazio, pot = blinds+antes
        hand.streets[Street.PREFLOP] = StreetRecord(
            street=Street.PREFLOP,
            board_before=[],
            pot_before=table_info.pot,
        )

        self.session.hands.append(hand)
        self.session.last_hand_id = table_info.hand

    def _close_current_hand(self) -> None:
        hand = self.session.current_hand
        if hand and hand.ended_at is None:
            hand.ended_at = time.time()

    def _extract_actions_from_badges(
        self,
        hand: HandRecord,
        table_info: TableInfo,
        street: Street,
    ) -> None:
        """
        Extrai acoes observadas nos last_action dos players e anexa a street.

        Ordenacao: usa pos_preflop (PREFLOP) ou ordem pos-flop (demais streets).
        Nao eh perfeito (nao temos timestamp individual de cada acao vindo do
        site); para ordem precisa, o recognizer precisa capturar badges
        incrementalmente ao longo do tempo.
        """
        sr = hand.streets.get(street)
        if not sr:
            return

        # Players que ja temos acao registrada nesta street
        existing = {a.player_name for a in sr.actions}
        next_order = len(sr.actions) + 1

        # Ordem de acao dependendo da street
        order = (POSITION_ORDER_PREFLOP if street == Street.PREFLOP
                 else POSITION_ORDER_POSTFLOP)

        def order_key(p: Player) -> int:
            if p.pos_preflop is None:
                return 999
            try:
                return order.index(p.pos_preflop)
            except ValueError:
                return 999

        candidates = sorted(
            [p for p in table_info.players
             if p.last_action is not None and p.name not in existing],
            key=order_key,
        )

        for player in candidates:
            action = Action(
                order=next_order,
                player_name=player.name,
                seat=player.seat,
                type=player.last_action,
                amount=player.last_action_amount,
                street=street,
            )
            sr.actions.append(action)
            next_order += 1

    def _process_showdown(self, hand: HandRecord, table_info: TableInfo) -> None:
        """Coleta cartas mostradas nos players e (se disponivel) vencedores."""
        for p in table_info.players:
            if p.shown_cards:
                # O Player ja carrega shown_cards; nada a fazer no HandRecord
                # alem de manter referencia. Vencedores viriam de um campo
                # dedicado no TableInfo (a ser adicionado quando o recognizer
                # souber ler o indicador de vencedor).
                pass
