# Loop de treinamento melhorado
import torch
import numpy as np
from tqdm import tqdm
from pk_agent.dqn.agent.dqn_agent import DQNAgent
from pk_agent.dqn.train.slumbot_env import SlumbotEnv
from pk_agent.dqn.train.state_representation import PokerStateRepresentation
from pk_agent.dqn.train.reward_system import PokerRewardSystem
import matplotlib.pyplot as plt
import os
import re

def train(episodes=10000, save_path="models", username=None, password=None):
    # Configuração do ambiente e do agente
    env = SlumbotEnv(username=username, password=password)
    state_rep = PokerStateRepresentation()
    reward_system = PokerRewardSystem()
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Usando dispositivo: {device}")
    
    # Dimensão do estado e número de ações
    state_dim = 133  # Atualizado conforme nova representação de estado
    action_dim = 3   # fold, call/check, bet/raise
    
    agent = DQNAgent(state_dim, action_dim, device)
    
    # Métricas de treinamento
    rewards = []
    avg_rewards = []
    losses = []
    total_rewards = 0  # Adiciona acumulador de recompensas totais
    
    # Cria diretório para salvar modelos
    os.makedirs(save_path, exist_ok=True)
    
    # Importe bibliotecas necessárias
    import matplotlib.pyplot as plt
    import numpy as np
    
    # Adicione estruturas de dados para monitoramento
    loss_history = []
    reward_history = []
    avg_reward_history = []
    epsilon_history = []
    
    # Função auxiliar para extrair valores de apostas da string de ação
    def extract_bet_amounts(action_str):
        # Usa expressão regular para encontrar todos os valores numéricos após 'b'
        bet_amounts = []
        for street in action_str.split('/'):
            # Encontra todos os padrões 'b' seguidos por números
            matches = re.findall(r'b(\d+)', street)
            bet_amounts.extend([int(match) for match in matches])
        return bet_amounts
    
    # Substitua num_episodes por episodes aqui
    for episode in range(episodes):
        # Reseta o ambiente e sistemas
        state_info = env.reset()
        reward_system.reset()
        done = False
        episode_reward = 0
        episode_losses = []
        
        # Converte o estado usando a nova representação
        hole_cards = env.last_response.get('hole_cards', [])
        board_cards = env.last_response.get('board', [])
        pot_size = 0  # Inicialmente zero
        stack_size = env.stack_size
        bet_history = env.last_response.get('action', '')
        position = env.last_response.get('client_pos', 0)
        num_players = 2  # Simplificado
        
        state = state_rep.create_state_vector(
            hole_cards, board_cards, pot_size, stack_size, 
            bet_history, position, num_players
        )
        
        # Loop de uma mão
        while not done:
            # Agente escolhe uma ação
            action_idx = agent.act(state)
            
            # Converte índice para ação
            action_map = {0: 'f', 1: 'c', 2: 'b'}
            action_str = action_map[action_idx]
            
            # Executa a ação no ambiente
            next_state_raw, reward_raw, done, info = env.step(action_idx)
            
            # Extrai informações atualizadas
            hole_cards = env.last_response.get('hole_cards', [])
            board_cards = env.last_response.get('board', [])
            
            # Estima o pot_size usando a função auxiliar
            action_string = env.last_response.get('action', '')
            bet_amounts = extract_bet_amounts(action_string)
            pot_size = sum(bet_amounts) * 2  # Multiplica por 2 para considerar ambos os jogadores
            
            stack_size = env.stack_size
            bet_history = env.last_response.get('action', '')
            position = env.last_response.get('client_pos', 0)
            
            # Calcula call_amount (simplificado)
            call_amount = bet_amounts[-1] if bet_amounts else 0
            
            # Converte para o novo formato de estado
            next_state = state_rep.create_state_vector(
                hole_cards, board_cards, pot_size, stack_size, 
                bet_history, position, num_players
            )
            
            # Calcula recompensa usando o sistema melhorado
            reward = reward_system.calculate_reward(
                action_str, reward_raw, pot_size, stack_size,
                hole_cards, board_cards, call_amount, done,
                position, num_players
            )
            
            # Calcula erro TD inicial para priorização
            with torch.no_grad():
                state_tensor = torch.from_numpy(np.array([state])).float().to(device)
                next_state_tensor = torch.from_numpy(np.array([next_state])).float().to(device)
                
                current_q = agent.policy_net(state_tensor)[0][action_idx].item()
                next_q = agent.target_net(next_state_tensor)[0].max().item()
                
                expected_q = reward + (1 - done) * agent.gamma * next_q
                td_error = abs(current_q - expected_q)
            
            # Armazena a experiência com o erro TD
            agent.remember(state, action_idx, reward, next_state, done, error=td_error)
            
            # Aprende com a experiência
            loss = agent.learn()
            if loss is not None:
                episode_losses.append(loss)
            
            # Atualiza para o próximo passo
            state = next_state
            episode_reward += reward
        
        # Fim do episódio
        rewards.append(episode_reward)
        total_rewards += episode_reward  # Acumula a recompensa total
        avg_reward = np.mean(rewards[-100:]) if len(rewards) >= 100 else np.mean(rewards)
        avg_rewards.append(avg_reward)
        
        if episode_losses:
            losses.append(np.mean(episode_losses))
        
        # Exibe progresso com total acumulado
        if episode % 10 == 0:
            print(f"Episódio {episode}, Recompensa: {episode_reward:.2f}, Média: {avg_reward:.2f}, Total: {total_rewards:.2f}, ε: {agent.epsilon:.2f}, Loss: {np.mean(episode_losses) if episode_losses else 0:.4f}")
        
        # Salva o modelo periodicamente
        if episode % 100 == 0:
            torch.save({
                'policy_net': agent.policy_net.state_dict(),
                'target_net': agent.target_net.state_dict(),
                'optimizer': agent.optimizer.state_dict(),
                'episode': episode,
                'epsilon': agent.epsilon
            }, f"{save_path}/dqn_poker_ep{episode}.pt")
    
        # Após calcular a perda
        if loss is not None:
            loss_history.append(loss)
        reward_history.append(episode_reward)
        avg_reward_history.append(avg_reward)
        epsilon_history.append(agent.epsilon)
        
        # A cada 500 episódios, plote os gráficos intermediários
        if episode % 500 == 0 and episode > 0:
            plt.figure(figsize=(15, 10))
            
            # Gráfico de Perda
            plt.subplot(2, 2, 1)
            plt.plot(loss_history)
            plt.title('Perda ao Longo do Tempo')
            plt.xlabel('Episódio')
            plt.ylabel('Perda')
            
            # Gráfico de Recompensa
            plt.subplot(2, 2, 2)
            plt.plot(reward_history)
            plt.title('Recompensa por Episódio')
            plt.xlabel('Episódio')
            plt.ylabel('Recompensa')
            
            # Gráfico de Recompensa Média
            plt.subplot(2, 2, 3)
            plt.plot(avg_reward_history)
            plt.title('Recompensa Média (100 episódios)')
            plt.xlabel('Episódio')
            plt.ylabel('Recompensa Média')
            
            # Gráfico de Epsilon
            plt.subplot(2, 2, 4)
            plt.plot(epsilon_history)
            plt.title('Valor de Epsilon')
            plt.xlabel('Episódio')
            plt.ylabel('Epsilon')
            
            plt.tight_layout()
            plt.savefig(f'training_progress_episode_{episode}.png')
            plt.close()
            
            # Salve também os dados brutos para análise posterior
            np.save(f'training_data_episode_{episode}.npy', {
                'loss': loss_history,
                'reward': reward_history,
                'avg_reward': avg_reward_history,
                'epsilon': epsilon_history
            })
    
    # Salva o modelo final
    torch.save({
        'policy_net': agent.policy_net.state_dict(),
        'target_net': agent.target_net.state_dict(),
        'optimizer': agent.optimizer.state_dict(),
        'episode': episodes-1,
        'epsilon': agent.epsilon
    }, f"{save_path}/dqn_poker_final.pt")
    
    # Plota resultados
    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    plt.plot(rewards, alpha=0.3)
    plt.plot(avg_rewards)
    plt.title('Recompensas por Episódio')
    plt.xlabel('Episódio')
    plt.ylabel('Recompensa')
    
    plt.subplot(1, 2, 2)
    plt.plot(losses)
    plt.title('Perda Média por Episódio')
    plt.xlabel('Episódio')
    plt.ylabel('Perda')
    
    plt.tight_layout()
    plt.savefig(f"{save_path}/training_results.png")
    plt.show()
    
    # Adiciona impressão final do total acumulado
    print(f"\nTreinamento concluído! Recompensa total acumulada: {total_rewards:.2f}")
    
    return agent
