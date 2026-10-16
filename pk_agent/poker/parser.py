import re
import json
from pathlib import Path

def parse_hand_history(file_path):
    with open(file_path, 'r') as f:
        raw = f.read()

    hands = raw.strip().split("\n\n")  # cada hand separada
    parsed_hands = []

    for hand in hands:
        lines = hand.strip().split("\n")
        parsed = parse_single_hand(lines)
        if parsed:
            parsed_hands.append(parsed)

    return parsed_hands

def parse_single_hand(lines):
    state = {
        "starting_stacks": [],
        "actions": [],
        "board": [],
        "hole_cards": {},
        "player_positions": ["SB", "BB"],  # assume HU fixo
        "winner": None
    }

    # Extrair stacks iniciais
    for line in lines:
        if "starting_stacks" in line:
            stack_line = re.findall(r"\[(.*?)\]", line)
            if stack_line:
                state["starting_stacks"] = list(map(float, stack_line[0].split(',')))

    # Extrair ações do array 'actions' se existir
    for line in lines:
        if line.strip().startswith("actions = ["):
            # Extrair as ações entre colchetes
            actions_match = re.search(r"actions = \[(.*?)\]", line)
            if actions_match:
                action_strings = actions_match.group(1).split(', ')
                # Remover aspas simples ou duplas
                action_strings = [s.strip('\'"') for s in action_strings]
                
                for action_str in action_strings:
                    if action_str.startswith('p') and not "dh" in action_str:
                        parsed_action = parse_action_line(action_str)
                        if parsed_action:
                            state["actions"].append(parsed_action)
            break

    # Se não encontrou no array actions, procura linha por linha
    if not state["actions"]:
        for line in lines:
            if line.strip().startswith("p") and not "dh" in line:  # Pega todas as ações de jogadores, excluindo as cartas distribuídas
                parsed_action = parse_action_line(line)
                if parsed_action:
                    state["actions"].append(parsed_action)

    # Board (ex: d db 9c9hTc)
    for line in lines:
        if line.startswith("d db"):
            cards = line.split(" ")[-1]
            state["board"].extend([cards[i:i+2] for i in range(0, len(cards), 2)])

    # Hole cards (simplificado, se aparecerem)
    for line in lines:
        if "sm" in line:
            parts = line.strip().split(" ")
            pid = 0 if parts[0] == "p1" else 1
            state["hole_cards"][str(pid)] = [parts[-1][:2], parts[-1][2:]]

    return state

def parse_action_line(line):
    # exemplo: p1 cb 1.00 ou p3 cbr 1.75
    tokens = line.strip().split()
    if len(tokens) < 2:
        return None
        
    # Ignorar linhas que começam com 'd' (dealer actions)
    if tokens[0] == 'd':
        return None

    # Extrair o número do jogador (p1, p2, p3, etc.)  
    player_match = re.match(r'p(\d+)', tokens[0])
    if player_match:
        player = int(player_match.group(1)) - 1  # Converter para índice baseado em 0
    else:
        player = 0  # Valor padrão se não conseguir extrair
    
    action_code = tokens[1]
    
    # Verificar se há um valor numérico para amount
    amount = None
    if len(tokens) > 2 and tokens[2] not in ['????']:
        try:
            amount = float(tokens[2])
        except ValueError:
            # Se não conseguir converter para float, deixa como None
            pass

    action_map = {
        "f": "fold",
        "cc": "call",
        "cb": "bet",  # cb parece ser bet
        "cbr": "raise",
        "sm": "show",
    }

    return {
        "player": player,
        "action": action_map.get(action_code, "unknown"),
        "amount": amount
    }

# Debug
if __name__ == "__main__":
    path = "pk_agent/data/phh/abs NLH handhq_8-OBFUSCATED.phhs"
    parsed = parse_hand_history(path)
    print(parsed)
    Path("pk_agent/parsed").mkdir(exist_ok=True)
    with open("pk_agent/parsed/hands.json", "w") as f:
        json.dump(parsed, f, indent=2)
