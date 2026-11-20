"""
pk_agent/slumbot/client.py
O unico cliente HTTP do Slumbot (https://slumbot.com/api), usado pelo ambiente e pelo smoke test.

  - requests.Session: reaproveita a conexao TCP/TLS entre chamadas (um requests.post solto abre uma
    nova a cada vez; num treino sao milhares de chamadas);
  - timeout: sem ele, uma conexao travada pendura o treino para sempre.
"""
import os
from typing import Optional, Tuple

import requests

HOST = "https://slumbot.com"
TIMEOUT = 20          # segundos, por chamada


class SlumbotError(Exception):
    """Resposta do Slumbot que nao da para usar (sem JSON, sem token, login recusado)."""


def credentials_from_env() -> Tuple[Optional[str], Optional[str]]:
    """(usuario, senha) de SLUMBOT_USERNAME / SLUMBOT_PASSWORD, ou (None, None).
    Sem login o Slumbot ainda joga, so nao guarda o historico na sua conta. Nunca escreva a senha no codigo."""
    username, password = os.environ.get("SLUMBOT_USERNAME"), os.environ.get("SLUMBOT_PASSWORD")
    return (username, password) if username and password else (None, None)


class SlumbotClient:
    def __init__(self, host: str = HOST, timeout: float = TIMEOUT, session: Optional[requests.Session] = None):
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.token: Optional[str] = None

    def _post(self, path: str, payload: dict) -> requests.Response:
        return self.session.post(f"{self.host}{path}", json=payload, timeout=self.timeout)

    def _json(self, response: requests.Response) -> dict:
        try:
            data = response.json()
        except ValueError:
            raise SlumbotError("a resposta nao veio em JSON") from None
        if data.get("token"):
            self.token = data["token"]
        return data

    def login(self, username: str, password: str) -> str:
        """Entra na conta; guarda e devolve o token. Levanta SlumbotError se recusar."""
        response = self._post("/api/login", {"username": username, "password": password})
        if response.status_code != 200:
            detail = ""
            try:
                detail = f": {response.json()}"
            except ValueError:
                pass
            raise SlumbotError(f"login recusado (HTTP {response.status_code}){detail}")
        data = self._json(response)
        if "error_msg" in data:
            raise SlumbotError(f"login recusado: {data['error_msg']}")
        if not self.token:
            raise SlumbotError("o login nao devolveu token")
        return self.token

    def new_hand(self) -> dict:
        """Comeca uma mao nova (levanta requests.HTTPError se o servidor devolver erro HTTP)."""
        response = self._post("/api/new_hand", {"token": self.token} if self.token else {})
        response.raise_for_status()
        return self._json(response)

    def act(self, incr: str) -> dict:
        """Envia uma acao ('f', 'c', 'k' ou 'b<valor>') e devolve o novo estado da mao."""
        response = self._post("/api/act", {"token": self.token, "incr": incr})
        response.raise_for_status()
        return self._json(response)
