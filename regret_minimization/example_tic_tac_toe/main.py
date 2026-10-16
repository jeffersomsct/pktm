import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random

# Definição do tabuleiro e funções auxiliares
def evaluate(board):
    """
    Avalia o resultado do tabuleiro.
    Retorna: +1 Vitória Player 1 | -1 Vitória Player 2 | 0 Empate ou incompleto.
    """
    for row in board:
        if row[0] == row[1] == row[2] != 0:
            return row[0]
    for col in range(3):
        if board[0][col] == board[1][col] == board[2][col] != 0:
            return board[0][col]
    if board[0][0] == board[1][1] == board[2][2] != 0:
        return board[0][0]
    if board[0][2] == board[1][1] == board[2][0] != 0:
        return board[0][2]
    return 0

def get_valid_actions(board):
    """Retorna as ações válidas no estado atual."""
    return [(i, j) for i in range(3) for j in range(3) if board[i][j] == 0]

def encode_board(board, player):
    """
    Codifica o tabuleiro como entrada para a rede neural.
    Representa o tabuleiro como um tensor de tamanho (2, 3, 3):
    - Canal 0: Posições do jogador atual.
    - Canal 1: Posições do adversário.
    """
    encoded = np.zeros((2, 3, 3), dtype=np.float32)
    for i in range(3):
        for j in range(3):
            if board[i][j] == player:
                encoded[0][i][j] = 1
            elif board[i][j] == -player:
                encoded[1][i][j] = 1
    return torch.tensor(encoded, dtype=torch.float32)

# Redes Neurais
class RegretNetwork(nn.Module):
    def __init__(self):
        super(RegretNetwork, self).__init__()
        self.fc1 = nn.Linear(18, 128)  # Entrada: 2 canais * 3x3 = 18
        self.fc2 = nn.Linear(128, 128)
        self.fc3 = nn.Linear(128, 9)  # Saída: 9 ações possíveis

    def forward(self, x):
        x = x.view(x.size(0), -1)  # Flatten
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

class StrategyNetwork(nn.Module):
    def __init__(self):
        super(StrategyNetwork, self).__init__()
        self.fc1 = nn.Linear(18, 128)
        self.fc2 = nn.Linear(128, 128)
        self.fc3 = nn.Linear(128, 9)
    
    def forward(self, x):
        x = x.view(x.size(0), -1)  # Flatten
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return torch.softmax(self.fc3(x), dim=-1)

# Treinamento Deep CFR
def train_tic_tac_toe(iterations=10000, learning_rate=0.001):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(device)
    regret_network = RegretNetwork().to(device)
    strategy_network = StrategyNetwork().to(device)
    optimizer_regret = optim.Adam(regret_network.parameters(), lr=learning_rate)
    optimizer_strategy = optim.Adam(strategy_network.parameters(), lr=learning_rate)
    criterion = nn.MSELoss()

    avg_regret_loss = 0
    avg_strategy_loss = 0
    results = []

    for iteration in range(iterations):
        # Inicializa o tabuleiro
        board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        player = 1
        history = []
        regret_losses = []
        strategy_losses = []

        # Simula uma partida
        while evaluate(board) == 0 and any(cell == 0 for row in board for cell in row):
            encoded_board = encode_board(board, player)
            valid_actions = get_valid_actions(board)

            # Calcula probabilidades de ação usando a estratégia atual
            # Calcula as probabilidades de ação usando a estratégia atual
            with torch.no_grad():
                action_probs = strategy_network(encoded_board.unsqueeze(0)).squeeze().numpy()

            # Filtra apenas as ações válidas
            valid_actions = get_valid_actions(board)
            if not valid_actions:
                raise ValueError("Nenhuma ação válida disponível. O jogo terminou.")

            action_probs = [action_probs[i * 3 + j] if (i, j) in valid_actions else 0 for i in range(3) for j in range(3)]

            # Converte para array numpy e normaliza
            action_probs = np.array(action_probs)
            if action_probs.sum() == 0:
                raise ValueError("As probabilidades são todas zero. Verifique as ações válidas e o modelo.")

            action_probs += 1e-10  # Adiciona uma pequena constante para evitar zeros
            action_probs /= action_probs.sum()  # Normaliza para garantir que a soma seja 1

            # Escolhe uma ação com base nas probabilidades
            action_idx = np.random.choice(len(action_probs), p=action_probs)
            action = (action_idx // 3, action_idx % 3)

            # Escolhe uma ação baseada nas probabilidades
            action_idx = np.random.choice(len(action_probs), p=action_probs)
            action = (action_idx // 3, action_idx % 3)
            history.append((encoded_board, action, player))

            # Atualiza o tabuleiro
            board[action[0]][action[1]] = player
            player = -player

        # Retropropagação de arrependimento
        result = evaluate(board)
        results.append(result)
        regrets = []
        for encoded_board, action, current_player in reversed(history):
            valid_actions = get_valid_actions(board)
            with torch.no_grad():
                action_probs = strategy_network(encoded_board.unsqueeze(0)).squeeze().numpy()

            # Calcula o valor hipotético para cada ação
            hypothetical_values = []
            for i, j in valid_actions:
                hypothetical_board = [row[:] for row in board]
                hypothetical_board[i][j] = current_player
                hypothetical_values.append(evaluate(hypothetical_board))

            # Calcula o arrependimento para todas as 9 ações (preenche 0 para inválidas)
            actual_value = evaluate(board)
            regret_full = []
            idx = 0
            for i in range(3):
                for j in range(3):
                    if (i, j) in valid_actions:
                        regret_full.append(max(0, hypothetical_values[idx] - actual_value))
                        idx += 1
                    else:
                        regret_full.append(0.0)
            regrets.append(regret_full)

            # Atualiza a rede de arrependimento
            optimizer_regret.zero_grad()
            predicted_regrets = regret_network(encoded_board.unsqueeze(0)).squeeze()
            loss = criterion(predicted_regrets, torch.tensor(regret_full, dtype=torch.float32))
            loss.backward()
            optimizer_regret.step()
            regret_losses.append(loss.item())

        # Atualiza a rede de estratégia média
        optimizer_strategy.zero_grad()
        for encoded_board, _, _ in history:
            predicted_strategy = strategy_network(encoded_board.unsqueeze(0)).squeeze()
            target_strategy = regret_network(encoded_board.unsqueeze(0)).squeeze()
            loss = criterion(predicted_strategy, target_strategy)
            loss.backward()
            strategy_losses.append(loss.item())
        optimizer_strategy.step()

        # Imprime progresso detalhado
        if (iteration + 1) % 1000 == 0:
            avg_regret_loss = np.mean(regret_losses) if regret_losses else 0
            avg_strategy_loss = np.mean(strategy_losses) if strategy_losses else 0
            win_rate_p1 = (np.array(results[-1000:]) == 1).mean()
            win_rate_p2 = (np.array(results[-1000:]) == -1).mean()
            draw_rate = (np.array(results[-1000:]) == 0).mean()
            print(f"Iteração {iteration + 1}: "
                  f"Regret Loss={avg_regret_loss:.4f}, "
                  f"Strategy Loss={avg_strategy_loss:.4f}, "
                  f"Win P1={win_rate_p1:.2%}, "
                  f"Win P2={win_rate_p2:.2%}, "
                  f"Draw={draw_rate:.2%}")

# Função para jogar contra o agente
def play_against_agent(strategy_network):
    board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    player = 1

    while evaluate(board) == 0 and any(cell == 0 for row in board for cell in row):
        print("\nTabuleiro:")
        for row in board:
            print(row)

        if player == 1:  # Jogador humano
            print("Sua vez (jogador X). Insira a linha e coluna (0-2):")
            try:
                row, col = map(int, input("Linha Coluna: ").split())
                while board[row][col] != 0:
                    print("Posição ocupada! Tente novamente.")
                    row, col = map(int, input("Linha Coluna: ").split())
                board[row][col] = 1
            except ValueError:
                print("Entrada inválida! Insira dois números separados por espaço, como '0 2'.")
                continue
        else:  # Agente IA
            print("Vez do agente (jogador O).")
            encoded_board = encode_board(board, player)
            with torch.no_grad():
                action_probs = strategy_network(encoded_board.unsqueeze(0)).squeeze().numpy()
            valid_actions = get_valid_actions(board)
            action_probs = [action_probs[i * 3 + j] if (i, j) in valid_actions else 0 for i in range(3) for j in range(3)]
            action_probs /= sum(action_probs)
            action_idx = np.random.choice(len(action_probs), p=action_probs)
            action = (action_idx // 3, action_idx % 3)
            board[action[0]][action[1]] = -1

        player = -player

    print("\nResultado final:")
    for row in board:
        print(row)

    result = evaluate(board)
    if result == 1:
        print("Você venceu!")
    elif result == -1:
        print("O agente venceu!")
    else:
        print("Empate!")

# Execução principal
if __name__ == "__main__":
    print("Iniciando treinamento...")
    train_tic_tac_toe(iterations=10000)
    print("Treinamento concluído!")

    print("\nJogar contra o agente?")
    choice = input("Digite 's' para sim ou qualquer outra tecla para sair: ")
    if choice.lower() == 's':
        strategy_network = StrategyNetwork()
        play_against_agent(strategy_network)