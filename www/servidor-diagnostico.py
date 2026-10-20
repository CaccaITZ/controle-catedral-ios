#!/usr/bin/env python3
"""
Servidor local de diagnóstico do Controle Catedral.
Sirve index-diagnostico.html e encaminha as chamadas da API do Holyrics,
evitando o bloqueio de CORS que ocorre ao abrir o HTML com file://.
Use somente no computador confiável onde o Holyrics está instalado.
"""
import http.client
import json
import os
import re
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

HOST = "127.0.0.1"
PORT = 8765
API_PORT = 4545

class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Não imprimir a query string, pois ela pode conter o token da API.
        if self.path.startswith("/__proxy/api/"):
            action = self.path.split("?", 1)[0].rsplit("/", 1)[-1]
            print(f"[proxy API] {action}")
        else:
            super().log_message(fmt, *args)

    def _send_json_error(self, status, message):
        data = json.dumps({"status": "error", "error": message}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        parsed = urlsplit(self.path)
        prefix = "/__proxy/api/"
        if not parsed.path.startswith(prefix):
            return self._send_json_error(404, "Endpoint não encontrado no servidor local.")

        action = parsed.path[len(prefix):]
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", action):
            return self._send_json_error(400, "Nome de ação inválido.")

        query = parse_qs(parsed.query)
        host = (query.get("host") or [""])[0].strip()
        token = (query.get("token") or [""])[0]
        if not host or not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", host):
            return self._send_json_error(400, "IP ou nome do computador Holyrics inválido.")
        if not token:
            return self._send_json_error(400, "Token da API não foi informado.")

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 2_000_000:
                return self._send_json_error(413, "Corpo da requisição muito grande.")
            body = self.rfile.read(length) if length else b"{}"
            upstream = http.client.HTTPConnection(host, API_PORT, timeout=8)
            upstream_path = "/api/" + action + "?token=" + quote(token, safe="")
            upstream.request(
                "POST",
                upstream_path,
                body=body,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            response = upstream.getresponse()
            data = response.read()
            status = response.status
            content_type = response.getheader("Content-Type") or "application/json; charset=utf-8"
            upstream.close()

            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:
            # Mensagem sem token e sem URL completa.
            return self._send_json_error(502, "Proxy local não conseguiu consultar o Holyrics: " + str(exc))

def main():
    folder = Path(__file__).resolve().parent
    os.chdir(folder)
    index = folder / "index-diagnostico.html"
    if not index.exists():
        print("ERRO: index-diagnostico.html precisa estar na mesma pasta deste script.")
        input("Pressione Enter para sair...")
        return

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}/index-diagnostico.html"
    print("Servidor de diagnóstico ativo.")
    print("Abra no navegador: " + url)
    print("Deixe esta janela aberta durante o teste. Pressione Ctrl+C para encerrar.")
    try:
        webbrowser.open(url)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
