import requests
import sys
import numpy as np

host = 'https://slumbot.com'

class SlumbotAgent:
    def __init__(self, username=None, password=None):
        self.token = self.login(username, password) if username and password else None

    def login(self, username, password):
        data = {"username": username, "password": password}
        response = requests.post(f'{host}/api/login', json=data)
        response.raise_for_status()
        r = response.json()
        if 'token' not in r:
            raise Exception("Login failed: No token received.")
        return r['token']

    def reset(self):
        """Reseta o ambiente e retorna o estado inicial."""
        response = self.new_hand()
        # Retorna um estado inicial aleatório (ajuste conforme necessário)
        return np.random.rand(100)  # state_size = 100 conforme definido em train_loop.py

    def new_hand(self):
        data = {'token': self.token} if self.token else {}
        response = requests.post(f'{host}/api/new_hand', json=data)
        response.raise_for_status()
        r = response.json()
        self.token = r.get('token', self.token)
        return r

    def act(self, incr):
        data = {'token': self.token, 'incr': incr}
        response = requests.post(f'{host}/api/act', json=data)
        response.raise_for_status()
        r = response.json()
        self.token = r.get('token', self.token)
        return r
        
    def step(self, action):
        """Executa uma ação no ambiente e retorna (next_state, reward, done, info)."""
        # Executa a ação
        result = self.act(action)
        
        # Obtém o próximo estado (ajuste conforme necessário)
        next_state = np.random.rand(100)  # state_size = 100 conforme definido em train_loop.py
        
        # Calcula a recompensa (ajuste conforme sua lógica)
        reward = result.get('reward', 0)
        
        # Verifica se o episódio terminou
        done = result.get('done', False)
        
        # Info adicional pode ser vazio
        info = {}
        
        return next_state, reward, done, info
