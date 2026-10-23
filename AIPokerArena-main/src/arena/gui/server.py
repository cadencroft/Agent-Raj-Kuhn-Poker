"""Dependency-free localhost HTTP server for the Kuhn teaching GUI."""

# The embedded HTML/JavaScript is kept readable instead of wrapped as Python code.
# ruff: noqa: E501

from __future__ import annotations

import json
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from arena.gui.controller import KuhnGuiController

_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Poker Arena — Kuhn Poker</title>
  <style>
    :root { color-scheme: dark; font-family: ui-sans-serif, system-ui, sans-serif; }
    body { margin: 0; background: #10251e; color: #f7f4e9; }
    main { max-width: 760px; margin: 0 auto; padding: 32px 20px; }
    h1 { margin-bottom: 4px; }
    .subtle { color: #b8c9c1; }
    .table { margin-top: 24px; padding: 24px; border: 2px solid #ba9b55;
      border-radius: 28px; background: #174d38; box-shadow: 0 16px 50px #07120d99; }
    .row { display: flex; gap: 16px; justify-content: space-between; flex-wrap: wrap; }
    .seat { min-width: 180px; padding: 14px; border-radius: 12px; background: #0e3527; }
    .card { display: inline-grid; place-items: center; width: 58px; height: 78px;
      margin: 8px 4px 8px 0; border-radius: 8px; background: #fffaf0;
      color: #171717; font: bold 32px Georgia, serif; box-shadow: 0 3px 10px #0005; }
    .hidden { background: repeating-linear-gradient(45deg,#812b32,#812b32 7px,#e7c377 7px,#e7c377 10px); color: transparent; }
    .pot { margin: 22px 0; text-align: center; font-size: 22px; }
    button { margin: 5px; padding: 11px 18px; border: 0; border-radius: 8px;
      background: #f0c866; color: #17241f; font-weight: 700; cursor: pointer; }
    button:hover { background: #ffe49d; }
    ol { line-height: 1.7; }
    .result { font-size: 20px; font-weight: 700; color: #ffe49d; }
    .error { color: #ffb3b3; }
  </style>
</head>
<body><main>
  <h1>AI Poker Arena</h1>
  <div class="subtle">Human vs agent · Kuhn poker · private information enforced</div>
  <section class="table">
    <div class="row">
      <div class="seat"><strong id="bot-name">Bot</strong><div id="bot-stack"></div>
        <div id="bot-card" class="card hidden">?</div></div>
      <div class="seat"><strong id="human-name">You</strong><div id="human-stack"></div>
        <div id="human-card" class="card"></div></div>
    </div>
    <div class="pot">Pot: <strong id="pot"></strong> · To call: <strong id="call"></strong></div>
    <div id="result" class="result"></div>
    <div id="faults" class="subtle"></div>
    <div id="controls"></div>
    <div id="error" class="error"></div>
    <h3>Action history</h3><ol id="history"></ol>
  </section>
  <p class="subtle" id="hand"></p>
</main>
<script>
async function request(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}
function render(state) {
  const human = state.players.find(p => p.is_human);
  const bot = state.players.find(p => !p.is_human);
  const buttonLabel = seat => seat === state.dealer_seat ? ' · dealer' : '';
  document.querySelector('#bot-name').textContent = bot.player_id + buttonLabel(bot.seat);
  document.querySelector('#human-name').textContent = 'You' + buttonLabel(human.seat);
  document.querySelector('#bot-stack').textContent = `Stack: ${bot.stack} · Committed: ${bot.committed}`;
  document.querySelector('#human-stack').textContent = `Stack: ${human.stack} · Committed: ${human.committed}`;
  document.querySelector('#human-card').textContent = state.private_cards[0];
  const botCard = document.querySelector('#bot-card');
  const reveal = state.opponent_revealed_cards[0];
  botCard.textContent = reveal || '?';
  botCard.className = reveal ? 'card' : 'card hidden';
  document.querySelector('#pot').textContent = state.pot;
  document.querySelector('#call').textContent = state.amount_to_call;
  document.querySelector('#result').textContent = state.result_message || '';
  document.querySelector('#faults').textContent = state.bot_faults ? `Bot fallbacks this hand: ${state.bot_faults}` : '';
  document.querySelector('#hand').textContent = `Hand ${state.hand_number} · ${state.hand_id}`;
  const history = document.querySelector('#history');
  history.replaceChildren(...state.actions.map(a => {
    const item = document.createElement('li'); item.textContent = `${a.player_id}: ${a.label}`; return item;
  }));
  const controls = document.querySelector('#controls'); controls.replaceChildren();
  state.legal_actions.forEach(action => {
    const button = document.createElement('button'); button.textContent = action.label;
    button.onclick = () => act(action.action_id); controls.appendChild(button);
  });
  if (state.hand_complete) {
    const button = document.createElement('button'); button.textContent = 'Next hand';
    button.onclick = nextHand; controls.appendChild(button);
  }
}
async function act(actionId) {
  try { render(await request('/api/action', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action_id:actionId})})); }
  catch (error) { document.querySelector('#error').textContent = error.message; }
}
async function nextHand() {
  try { render(await request('/api/next', {method:'POST'})); }
  catch (error) { document.querySelector('#error').textContent = error.message; }
}
request('/api/state').then(render).catch(error => { document.querySelector('#error').textContent = error.message; });
</script></body></html>"""


def serve_gui(
    controller: KuhnGuiController,
    *,
    port: int = 8000,
    open_browser: bool = True,
) -> None:
    """Serve the GUI on loopback until interrupted."""
    handler = _handler_for(controller)
    server = HTTPServer(("127.0.0.1", port), handler)
    actual_port = server.server_address[1]
    url = f"http://127.0.0.1:{actual_port}"
    print(f"AI Poker Arena GUI: {url}")
    if open_browser:
        threading.Timer(0.2, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _handler_for(
    controller: KuhnGuiController,
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/":
                self._send_bytes(_PAGE.encode(), "text/html; charset=utf-8")
            elif self.path == "/api/state":
                self._send_json(controller.view().to_dict())
            else:
                self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            try:
                if self.path == "/api/action":
                    payload = self._read_json()
                    action_id = payload.get("action_id")
                    if not isinstance(action_id, str):
                        raise ValueError("action_id must be a string")
                    view = controller.submit_action(action_id)
                elif self.path == "/api/next":
                    view = controller.next_hand()
                else:
                    self._send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
                    return
                self._send_json(view.to_dict())
            except (ValueError, json.JSONDecodeError) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

        def log_message(self, format: str, *args: object) -> None:
            del format, args

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 4096:
                raise ValueError("Request body is too large")
            value = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(value, dict):
                raise ValueError("Request body must be a JSON object")
            return value

        def _send_json(
            self,
            value: object,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            self._send_bytes(
                json.dumps(value).encode(),
                "application/json; charset=utf-8",
                status,
            )

        def _send_bytes(
            self,
            body: bytes,
            content_type: str,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return Handler
