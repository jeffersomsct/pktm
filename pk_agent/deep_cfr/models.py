import torch
import torch.nn as nn
import torch.nn.functional as F

class ValueNetwork(nn.Module):
    """
    Rede neural para aproximar os valores de arrependimento ou estratégia no Deep CFR.
    """
    def __init__(self, input_dim, output_dim, hidden_dims=[256, 256]):
        super(ValueNetwork, self).__init__()
        
        # Camadas da rede
        layers = []
        prev_dim = input_dim
        
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.ReLU())
            prev_dim = hidden_dim
        
        # Camada de saída
        layers.append(nn.Linear(prev_dim, output_dim))
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x)

class AdvantageNetwork(nn.Module):
    """
    Rede neural para aproximar os valores de vantagem (advantage) no Deep CFR.
    """
    def __init__(self, input_dim, output_dim, hidden_dims=[256, 256]):
        super(AdvantageNetwork, self).__init__()
        
        # Camadas da rede
        layers = []
        prev_dim = input_dim
        
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.ReLU())
            prev_dim = hidden_dim
        
        # Camada de saída
        layers.append(nn.Linear(prev_dim, output_dim))
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x)