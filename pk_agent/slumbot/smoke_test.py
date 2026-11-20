"""
Teste rapido de conexao com o Slumbot: entra (se houver credenciais) e joga UMA mao so com check/call.

    set SLUMBOT_USERNAME=...   e   set SLUMBOT_PASSWORD=...     (Windows)
    python -m pk_agent.slumbot.smoke_test
"""
from pk_agent.slumbot.client import SlumbotClient, credentials_from_env

MAX_STEPS = 50       # uma mao so com check/call termina em poucos passos; isto evita laco infinito


def main():
    client = SlumbotClient()
    username, password = credentials_from_env()
    if username:
        client.login(username, password)
        print(f"Login ok como {username}.")
    else:
        print("Sem SLUMBOT_USERNAME/SLUMBOT_PASSWORD: jogando sem conta.")

    response = client.new_hand()
    print("Mao nova:", {k: response.get(k) for k in ("hole_cards", "client_pos", "action")})
    for _ in range(MAX_STEPS):
        if "winnings" in response or "error_msg" in response:
            break
        response = client.act("c")
        print("  c ->", {k: response.get(k) for k in ("action", "board", "winnings", "error_msg") if k in response})
    print("Resultado da mao (fichas):", response.get("winnings"))


if __name__ == "__main__":
    main()
