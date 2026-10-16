from slumbot_agent import SlumbotAgent
from env.holdem_env import HoldemEnv

def main():
    env = HoldemEnv(username='jess', password='1010350')

    total_hands = 10
    for i in range(total_hands):
        obs = env.reset()
        done = False
        print(f'\n=== Hand {i + 1} ===')
        while not done:
            print(f"Observation: {obs}")
            action = env.sample_action()  # Ação dummy por enquanto
            obs, reward, done, info = env.step(action)
            print(f"Action: {action} | Reward: {reward} | Done: {done}")
        print(f"Result: {info}")

if __name__ == '__main__':
    main()