from pk_agent.dqn.train.train_loop import train
from pk_agent.trainning.sample_api_slum import Login, PlayHand

if __name__ == "__main__":
    # Testar conexão com Slumbot
    username = 'jess'
    password = '1010350'
    token = Login(username, password)
    print(f"Conexão com Slumbot estabelecida. Token: {token}")
    
    # Jogar uma mão de teste
    PlayHand(token)
    
    # Iniciar treinamento com o token do Slumbot
    train(username=username, password=password)