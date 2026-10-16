from pk_agent.deep_cfr.train_deep_cfr import train_deep_cfr
from pk_agent.deep_cfr.poker_env_adapter import PokerEnvAdapter
import logging
import torch

if __name__ == "__main__":
    # Configura o logging para exibir informações detalhadas
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    # Seleciona o device automaticamente (GPU AMD via ROCm se disponível, senão CPU)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logging.info(f"Usando o device: {device}")
    
    # Cria o adaptador de ambiente
    env = PokerEnvAdapter()
    
    # Treina o agente Deep CFR
    agent = train_deep_cfr(num_iterations=100, save_path="models/deep_cfr")
    
    logging.info("Treinamento concluído com sucesso!")