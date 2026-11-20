"""
Servidor Slumbot FALSO, local, para testar o cliente e o ambiente sem internet.
Fala HTTP/1.1 com keep-alive (como o real) e conta quantas conexoes TCP recebeu.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOLE_CARDS = ["Ah", "Kd"]


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = 0
        self.requests = []            # (caminho, corpo) de cada chamada
        self.delay = 0.0              # segundos de espera antes de responder /api/act
        self.act_status = 200         # HTTP status de /api/act (para simular erro do servidor)

    def get_request(self):
        connection = super().get_request()
        self.connections += 1
        return connection


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _reply(self, payload, status=200, raw=None):
        body = raw if raw is not None else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        self.server.requests.append((self.path, body))
        hand = {"hole_cards": HOLE_CARDS, "board": [], "client_pos": 0}

        if self.path == "/api/login":
            password = body.get("password")
            if password == "ok":
                return self._reply({"token": "tok-1"})
            if password == "bad":
                return self._reply({"error_msg": "credenciais invalidas"}, status=403)
            if password == "nojson":
                return self._reply(None, raw=b"isto nao e json")
            return self._reply({})                                  # 200 sem token
        if self.path == "/api/new_hand":
            return self._reply({"token": body.get("token") or "tok-anon", "action": "", **hand})
        if self.path == "/api/act":
            if self.server.delay:
                time.sleep(self.server.delay)
            if self.server.act_status != 200:
                return self._reply({"error": "falha"}, status=self.server.act_status)
            incr = body.get("incr")
            if incr == "f":
                return self._reply({"action": "f", "winnings": -100, **hand})
            if incr == "x":
                return self._reply({"error_msg": "acao invalida", "old_action": ""})
            return self._reply({"action": incr, **hand})
        self._reply({}, status=404)


def start():
    """Sobe o servidor em uma porta livre. Devolve (servidor, url). Chame server.shutdown() ao fim."""
    server = _Server(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"
