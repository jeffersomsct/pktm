from abc import ABC, abstractmethod
from typing import Optional
import numpy as np
from poker_table_recognizer import TableInfo

class BasePokerRoom(ABC):
    """
    Classe abstrata que define a interface obrigatória para todas as salas de poker.
    
    Objetivo:
        - Garantir que todas as subclasses (como PokerRoom, TexasHoldemRoom, etc.) 
          implementem os métodos essenciais para análise de mesas de poker.
        - Funcionar como um contrato para padronização do código.

    Regras:
        1. Não pode ser instanciada diretamente (é uma ABC - Abstract Base Class).
        2. Todas as subclasses DEVEM implementar os métodos marcados com @abstractmethod.
    """

    @abstractmethod
    def analyze_table(self, snapshot: Optional[np.ndarray]) -> TableInfo:
        """
        Método abstrato para análise de um snapshot da mesa de poker.
        
        Parâmetros:
            snapshot (np.ndarray | None): Imagem da mesa (pode ser None em alguns casos).
        
        Retorna:
            TableInfo: Objeto contendo informações extraídas da análise (cartas, jogadores, etc.).
        
        Nota:
            - Cada subclasse deve implementar sua própria lógica de análise.
            - O tipo de retorno TableInfo é definido em core.table_analyzer.
        """
        pass
    
    @abstractmethod
    def get_room_config(self) -> dict:
        """
        Método abstrato para obter a configuração específica da sala.
        
        Retorna:
            dict: Dicionário com parâmetros de configuração (ex.: tipo de jogo, limites de aposta).
        
        Exemplo de retorno:
            {"game_type": "Texas Hold'em", "blinds": [100, 200]}
        """
        pass