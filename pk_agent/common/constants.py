# Ações básicas
FOLD = 0
CALL = 1
BET_2BB = 2  # Raise de 2 big blinds
BET_3BB = 3  # Raise de 3 big blinds
BET_5BB = 4  # Raise de 5 big blinds
BET_10BB = 5  # Raise de 10 big blinds
ALL_IN = 6   # All-in

# Lista de todas as ações
ACTION_LIST = [FOLD, CALL, BET_2BB, BET_3BB, BET_5BB, BET_10BB, ALL_IN]

# Mapeamento para strings de ação (sem valores específicos)
ACTION_STRINGS = {FOLD: 'f', CALL: 'c', BET_2BB: 'b', BET_3BB: 'b', BET_5BB: 'b', BET_10BB: 'b', ALL_IN: 'b'}

# Tamanhos de raise em big blinds
RAISE_SIZES_BB = {
    BET_2BB: 2,
    BET_3BB: 3,
    BET_5BB: 5,
    BET_10BB: 10,
    ALL_IN: float('inf')  # Representa all-in
}

def get_action_dim():
    return len(ACTION_LIST)