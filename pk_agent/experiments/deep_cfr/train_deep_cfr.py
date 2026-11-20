import torch
import numpy as np
import matplotlib.pyplot as plt
from pk_agent.experiments.deep_cfr.deep_cfr import DeepCFR
from pk_agent.dqn.train.slumbot_env import SlumbotEnv
import os
import time
from paths import DATA_DIR

def train_deep_cfr(num_iterations=100, save_path=DATA_DIR / "models" / "deep_cfr"):
    """
    Treina um agente Deep CFR para poker.
    """
    # Configuração do ambiente
    env = SlumbotEnv()
    
    # Importa as constantes para o espaço de ações
    from pk_agent.common.constants import get_action_dim
    
    # Dimensões do estado e ação
    state_dim = 138  # Conforme definido na representação de estado
    action_dim = get_action_dim()  # Usa a função para obter o número correto de ações
    
    # Dispositivo para treinamento
    if torch.cuda.is_available():
        device = torch.device("cuda")  # Usa GPU AMD com ROCm (identificada como "cuda")
    else:
        device = torch.device("cpu")
    print(f"Usando dispositivo: {device}")
    
    # Cria o agente Deep CFR
    agent = DeepCFR(state_dim, action_dim, num_players=2, device=device)
    
    # Cria diretório para salvar modelos
    os.makedirs(save_path, exist_ok=True)
    
    # Métricas de treinamento
    advantage_losses = [[] for _ in range(2)]
    strategy_losses = []
    
    # Loop de treinamento
    for iteration in range(1, num_iterations + 1):
        print(f"\nIteração {iteration}/{num_iterations}")
        iter_start = time.time()
        iter_adv_losses = [[] for _ in range(2)]
        
        # Para cada jogador
        for player_id in range(2):
            print(f"  Treinando jogador {player_id}")
            # Adiciona log detalhado para cada travessia
            for traversal in range(agent.num_traversals):
                state = env.reset()
                done = False
                step_count = 0
                while not done:
                    # Obtém as ações legais para o estado atual
                    legal_actions = env.get_legal_actions()
                    # O agente só pode escolher entre as ações legais
                    action = agent.select_action(state, legal_actions)
                    next_state, reward, done, info = env.step(action)
                    action_desc = info.get('action_description', str(action))

                    print(f"    [Iter {iteration} | Jogador {player_id} | Travessia {traversal} | Passo {step_count}] "
                          f"Ação: {action} ({action_desc}), Recompensa: {reward}, Done: {done}")
                    state = next_state
                    step_count += 1
            
            # Realiza travessias do jogo para coletar experiências
            for _ in range(agent.num_traversals):
                # Reseta o ambiente
                state = env.reset()
                done = False
                
                while not done:
                    
                    action = agent.select_action(state, legal_actions)
                    
                    # Executa a ação
                    next_state, reward, done, info = env.step(action)
                    
                    # Atualiza o estado
                    state = next_state
            
            # Atualiza a rede de vantagem
            advantage_loss = agent._update_advantage_network(player_id, iteration)
            if advantage_loss:
                advantage_losses[player_id].append(advantage_loss)
                iter_adv_losses[player_id].append(advantage_loss)
                print(f"    Perda de vantagem: {advantage_loss:.4f}")
        
        # Atualiza a rede de estratégia
        strategy_loss = agent._update_strategy_network(iteration)
        if strategy_loss:
            strategy_losses.append(strategy_loss)
            print(f"  Perda de estratégia: {strategy_loss:.4f}")
        
        # Estatísticas da iteração
        for player_id in range(2):
            if iter_adv_losses[player_id]:
                avg_loss = np.mean(iter_adv_losses[player_id])
                min_loss = np.min(iter_adv_losses[player_id])
                max_loss = np.max(iter_adv_losses[player_id])
                print(f"    Jogador {player_id} - Perda de vantagem média: {avg_loss:.4f} (min: {min_loss:.4f}, max: {max_loss:.4f})")
        if strategy_loss:
            print(f"  Perda de estratégia nesta iteração: {strategy_loss:.4f}")
        print(f"  Tempo da iteração: {time.time() - iter_start:.2f}s")
        
        # Salva o modelo periodicamente
        if iteration % 10 == 0:
            agent.save_model(f"{save_path}/deep_cfr_iter_{iteration}.pt")
            # Salva gráfico intermediário
            plt.figure(figsize=(15, 5))
            plt.subplot(1, 3, 1)
            for player_id in range(2):
                plt.plot(advantage_losses[player_id], label=f"Jogador {player_id}")
            plt.title('Perda de Vantagem por Iteração')
            plt.xlabel('Atualização')
            plt.ylabel('Perda')
            plt.legend()
            plt.subplot(1, 3, 2)
            plt.plot(strategy_losses)
            plt.title('Perda de Estratégia por Iteração')
            plt.xlabel('Atualização')
            plt.ylabel('Perda')
            plt.tight_layout()
            plt.savefig(f"{save_path}/training_progress_iter_{iteration}.png")
            plt.close()
    
    # Salva o modelo final
    agent.save_model(f"{save_path}/deep_cfr_final.pt")
    
    # Plota resultados
    plt.figure(figsize=(15, 5))
    
    plt.subplot(1, 3, 1)
    for player_id in range(2):
        plt.plot(advantage_losses[player_id], label=f"Jogador {player_id}")
    plt.title('Perda de Vantagem por Iteração')
    plt.xlabel('Atualização')
    plt.ylabel('Perda')
    plt.legend()
    
    plt.subplot(1, 3, 2)
    plt.plot(strategy_losses)
    plt.title('Perda de Estratégia por Iteração')
    plt.xlabel('Atualização')
    plt.ylabel('Perda')
    
    plt.tight_layout()
    plt.savefig(f"{save_path}/training_results.png")
    plt.close()                       # sem plt.show(): ele prendia o processo ate fechar a janela
    
    print(f"\nTreinamento concluído!")
    
    return agent

if __name__ == "__main__":
    train_deep_cfr()