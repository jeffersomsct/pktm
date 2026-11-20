# experiments

Codigo que **nao** faz parte do caminho principal (DQN contra o Slumbot, em `pk_agent/dqn`).

## deep_cfr/

Esboco de Deep CFR. **Nao roda contra o Slumbot**, por um motivo estrutural: CFR precisa, a cada
decisao, calcular o valor de todas as acoes ramificando a mao (clonar o estado e voltar atras), e o
Slumbot e um servidor remoto que joga uma mao de cada vez. O `clone()` do `PokerEnvAdapter` cria um
ambiente novo e sem estado, entao os valores contrafactuais nao significam nada.

Para treinar CFR de verdade use um simulador local (por exemplo OpenSpiel ou RLCard) e deixe o
Slumbot so para **avaliar** o agente treinado.

O que foi corrigido aqui: a regra de decisao (`regret.py`, testada em `tests/test_deep_cfr_regret.py`)
levantava `ValueError: probabilities do not sum to 1` para qualquer rede sem vantagem positiva
(o caso normal de uma rede nao treinada) e, para os demais jogadores, por tamanhos diferentes
no `np.random.choice`.
