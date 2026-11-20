import re

import gymnasium as gym
import numpy as np
import requests
from gymnasium import spaces

from pk_agent.common.constants import (
    ACTION_STRINGS, ALL_IN, BET_2BB, BET_3BB, BET_5BB, BET_10BB, BIG_BLIND, CALL, FOLD,
    RAISE_SIZES_BB, STACK_SIZE,
)
from pk_agent.slumbot.client import SlumbotClient


class SlumbotEnv(gym.Env):
    def __init__(self, username=None, password=None, client=None):
        super(SlumbotEnv, self).__init__()
        self.client = client or SlumbotClient()          # um unico cliente HTTP (Session + timeout)
        if username and password:
            self.client.login(username, password)
        self.last_response = None
        self.stack_size = STACK_SIZE

        # Define os tamanhos de raise no estilo Pluribus (em big blinds)
        self.raise_sizes_bb = [2, 3, 5, 10]  # Você pode ajustar conforme desejar
        self.num_actions = 2 + len(self.raise_sizes_bb) + 1  # fold, call, raises, all-in
        self.action_space = spaces.Discrete(self.num_actions)
        self.observation_space = spaces.Box(low=0, high=1, shape=(138,), dtype=np.float32)

    @property
    def token(self):
        return self.client.token

    def new_hand(self):
        self.last_response = self.client.new_hand()
        return self.last_response

    def _act(self, incr):
        self.last_response = self.client.act(incr)
        return self.last_response

    def _convert_state(self, response):
        """
        Converte a resposta da API em um vetor de estado numpy
        """
        # Inicializa vetor de estado com zeros
        state = np.zeros(138)
        
        # Codifica as cartas do jogador (hole cards) - 52 posições (26 cartas * 2 naipes)
        if 'hole_cards' in response:
            for card in response['hole_cards']:
                idx = self._card_to_index(card)
                if idx is not None:
                    state[idx] = 1
        
        # Codifica as cartas do board - 52 posições
        if 'board' in response:
            for card in response['board']:
                idx = self._card_to_index(card)
                if idx is not None:
                    state[idx + 52] = 1
        
        # Codifica a posição do jogador (0 ou 1) - 2 posições
        if 'client_pos' in response:
            state[104 + response['client_pos']] = 1
        
        # Codifica o histórico de ações - 30 posições (6 tipos * 5 últimas ações)
        if 'action' in response:
            actions = response['action'].split('/')
            if actions:
                recent_actions = actions[-1][:5]  # Últimas 5 ações da street atual
                for i, action in enumerate(recent_actions):
                    if action == 'f':
                        state[106 + i*6] = 1
                    elif action == 'c':
                        state[107 + i*6] = 1
                    elif action == 'k':
                        state[108 + i*6] = 1
                    elif action.startswith('b'):
                        state[109 + i*6] = 1
                        # Normaliza o valor da aposta
                        try:
                            bet_amount = float(action[1:])
                            state[110 + i*6] = min(bet_amount / 10000, 1)  # Normaliza para [0,1]
                        except ValueError:
                            pass
        
        return state
    
    def _card_to_index(self, card):
        """
        Converte uma carta em um índice no vetor de estado
        """
        if len(card) != 2:
            return None
            
        values = {'2':0, '3':1, '4':2, '5':3, '6':4, '7':5, '8':6, '9':7, 'T':8, 'J':9, 'Q':10, 'K':11, 'A':12}
        suits = {'h':0, 'd':1, 's':2, 'c':3}
        
        value, suit = card[0], card[1]
        if value in values and suit in suits:
            return values[value] * 4 + suits[suit]
        return None

    def reset(self):
        """
        Reseta o ambiente iniciando uma nova mão.
        Retorna o estado inicial.
        """
        response = self.new_hand()  # Usa o método new_hand() já existente
        return self._convert_state(response)

    def _get_legal_raise_size(self, action_str):
        """
        Calcula o próximo raise legal com base na string de ações.
        """
        if not action_str:
            return BIG_BLIND * 2  # Primeiro bet/raise padrão

        # Extrai a última street de ação
        streets = action_str.strip('/').split('/')
        last_street = streets[-1] if streets else ''

        # Extrai apenas os valores numéricos de ações de raise usando regex
        bets = [int(match.group(1)) for match in re.finditer(r"b(\d+)", last_street)]

        if not bets:
            return 200

        last_bet = bets[-1]
        prev_bet = bets[-2] if len(bets) > 1 else 0
        increment = last_bet - prev_bet if prev_bet else last_bet
        next_raise = last_bet + increment

        return min(next_raise, self.stack_size)

    def _get_current_action(self):
        response = self.last_response
        if not response:
            return ''
        if response.get('error_msg'):
            return response.get('old_action', '')
        return response.get('action', '')
        
    def _calculate_remaining_stack(self, current_action):
        """
        Calcula o stack restante com base nas ações anteriores
        """
        remaining_stack = self.stack_size
        
        if not current_action:
            return remaining_stack
            
        # Divide as ações por street
        streets = current_action.strip('/').split('/')
        
        # Para cada street, calcula quanto foi apostado pelo jogador
        for street in streets:
            # Encontra todas as apostas feitas pelo jogador (posições pares na sequência de ações)
            actions = re.findall(r'[fck]|b\d+', street)
            for i, act in enumerate(actions):
                # Considera apenas ações do jogador (posições pares, começando do 0)
                if i % 2 == 0 and act.startswith('b'):
                    bet_amount = int(act[1:])
                    remaining_stack -= bet_amount
        
        return max(remaining_stack, 0)  # Garante que não fique negativo

    def _convert_action(self, action_idx):
        current_action = self._get_current_action()
        # Calcula o stack restante com base nas ações anteriores
        remaining_stack = self._calculate_remaining_stack(current_action)
        
        # Obtém o stack reportado pelo ambiente (se disponível)
        reported_stack = self.last_response.get('stack', remaining_stack) if self.last_response else remaining_stack
        
        # Usa o menor valor entre o calculado e o reportado para garantir segurança
        stack = min(remaining_stack, reported_stack)

        # Determina o mínimo raise permitido e o máximo legal
        min_raise = BIG_BLIND * 2
        if current_action:
            min_raise = self._get_legal_raise_size(current_action)
        
        # Verifica se há uma aposta pendente que precisa ser igualada
        pending_bet = 0
        if current_action:
            actions = re.findall(r'[fck]|b\d+', current_action)
            if actions and actions[-1].startswith('b'):
                pending_bet = int(actions[-1][1:])
        
        # Se o stack for menor ou igual ao valor pendente, só pode fazer call (all-in) ou fold
        if stack <= pending_bet and pending_bet > 0:
            if action_idx == FOLD:
                return ACTION_STRINGS[FOLD]
            else:  # Qualquer ação que não seja fold será convertida para call (all-in)
                return ACTION_STRINGS[CALL]
        
        # Converte o índice da ação para a string de ação
        if action_idx == FOLD:
            return ACTION_STRINGS[FOLD]
        elif action_idx == CALL:
            return ACTION_STRINGS[CALL]
        elif action_idx in [BET_2BB, BET_3BB, BET_5BB, BET_10BB]:
            # Se não tiver stack suficiente para o mínimo raise, converte para call
            if stack < min_raise:
                return ACTION_STRINGS[CALL]
                
            # Calcula o valor do raise com base no tamanho em big blinds
            bb_amount = RAISE_SIZES_BB[action_idx] * BIG_BLIND
            
            # O valor do raise não pode ser menor que o mínimo permitido, nem maior que o stack
            raise_amt = max(min(bb_amount, stack), min_raise)
            
            # Se o valor calculado for maior que o stack disponível, converte para all-in
            if raise_amt >= stack:
                return f"b{stack}"  # all-in
                
            return f"b{raise_amt}"
        elif action_idx == ALL_IN:
            return f"b{stack}"  # all-in
        else:
            raise ValueError(f"Índice de ação inválido: {action_idx}")

    def get_legal_actions(self):
        """
        Retorna uma lista de índices de ações legais no estado atual.
        """
        current_action = self._get_current_action()
        # Calcula o stack restante com base nas ações anteriores
        remaining_stack = self._calculate_remaining_stack(current_action)
        
        # Obtém o stack reportado pelo ambiente (se disponível)
        reported_stack = self.last_response.get('stack', remaining_stack) if self.last_response else remaining_stack
        
        # Usa o menor valor entre o calculado e o reportado para garantir segurança
        stack = min(remaining_stack, reported_stack)

        # Busca as ações da street atual
        actions = re.findall(r'[fck]|b\d+', current_action)
        last_bet = 0
        last_call = 0
        for act in actions:
            if act.startswith('b'):
                last_bet = int(act[1:])
            elif act == 'c':
                last_call = last_bet

        legal_actions = []

        # Verifica se há uma aposta pendente que precisa ser igualada
        pending_bet = 0
        if actions and actions[-1].startswith('b'):
            pending_bet = int(actions[-1][1:])
        
        # Se o stack for menor ou igual ao valor pendente, só pode fazer call (all-in) ou fold
        if stack <= pending_bet and pending_bet > 0:
            return [FOLD, CALL]  # Só pode foldar ou dar call (all-in)

        # Se houver aposta pendente, fold e call são permitidos
        if last_bet > last_call:
            legal_actions.append(FOLD)
            legal_actions.append(CALL)
        else:
            # Se o último adversário fez check, só check é permitido (representado por CALL)
            if actions and actions[-1] == 'k':
                legal_actions.append(CALL)
            # Se for o primeiro a agir na street, só check é permitido
            elif not actions or actions[-1] in ['c', '/']:
                legal_actions.append(CALL)

        # Raise só é permitido se houver stack suficiente para o mínimo raise
        min_raise = BIG_BLIND * 2
        if current_action:
            min_raise = self._get_legal_raise_size(current_action)
            
        if stack > min_raise:
            legal_actions += [BET_2BB, BET_3BB, BET_5BB, BET_10BB, ALL_IN]
        elif stack > 0 and stack > pending_bet:
            # Se tiver stack, mas não o suficiente para um raise mínimo, só pode all-in
            legal_actions.append(ALL_IN)

        return legal_actions

    def step(self, action_idx):
        """
        Executa uma ação (índice) no ambiente e retorna (next_state, reward, done, info).
        """
        try:
            # Usa o método _convert_action para mapear o índice da ação para a string de ação
            incr = self._convert_action(action_idx)
            result = self._act(incr)
            
            # Converte o estado para numpy array
            next_state = np.array(self._convert_state(result), dtype=np.float32)
            
            # Se a resposta contém 'winnings', a mão terminou
            if 'winnings' in result:
                reward = result['winnings']
                done = True
            elif 'error_msg' in result:
                reward = 0
                done = True
                print(result)
            else:
                reward = 0
                done = False
            
            # Adiciona a descrição da ação ao info
            info = result
            info['action_description'] = self.get_action_description(action_idx)

            return next_state, reward, done, info

        except requests.HTTPError as e:
            print(f'HTTP Error: {str(e)}')
            empty_state = np.zeros(138, dtype=np.float32)
            return empty_state, -1000, True, {'error': str(e)}
        except Exception as e:
            print(f'Error: {str(e)}')
            empty_state = np.zeros(138, dtype=np.float32)
            return empty_state, -1000, True, {'error': str(e)}

    def get_action_description(self, action_idx):
        """
        Retorna uma descrição legível da ação baseada no índice.
        """
        descriptions = {
            FOLD: "Fold",
            CALL: "Call/Check",
            BET_2BB: "Raise 2BB",
            BET_3BB: "Raise 3BB",
            BET_5BB: "Raise 5BB",
            BET_10BB: "Raise 10BB",
            ALL_IN: "All-In"
        }
        
        return descriptions.get(action_idx, f"Ação Desconhecida ({action_idx})")
