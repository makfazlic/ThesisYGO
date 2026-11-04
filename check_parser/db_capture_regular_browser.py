
import json
import queue
import threading
import webbrowser

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


REQUIRED_KEYS = {
    "turn",
    "me_hand", "me_GY", "me_banish",
    "me_field", "me_field_spell",
    "me_cards_in_deck", "me_cards_in_extra_deck",
    "me_life", "me_phase",
    "op_hand", "op_GY", "op_banish",
    "op_field", "op_field_spell",
    "op_cards_in_deck", "op_cards_in_extra_deck",
    "op_life", "op_phase",
}


CAPTURE_PAGE = b"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>DuelingBook Capture</title>
</head>
<body style="font:18px system-ui;margin:40px">

<p id="status">Sending game state to Python...</p>

<script>
(async () => {
    const status = document.getElementById("status");

    try {
        if (!location.hash) {
            throw new Error("No game-state data received");
        }

        const data = decodeURIComponent(
            location.hash.substring(1)
        );

        history.replaceState(null, "", "/capture");

        const response = await fetch("/api/capture", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: data
        });

        if (!response.ok) {
            throw new Error(await response.text());
        }

        status.textContent =
            "Captured successfully! State returned to Python.";

    } catch (error) {
        status.textContent = "Capture failed: " + error.message;
    }
})();
</script>

</body>
</html>
"""


def capture_replay_state(
    replay_id: int | str,
    *,
    port: int = 8765,
    timeout: int = 1800
) -> dict:

    responses = queue.Queue(maxsize=1)

    class CaptureHandler(BaseHTTPRequestHandler):

        def do_GET(self):
            if urlsplit(self.path).path != "/capture":
                self.send_error(404)
                return

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )
            self.send_header(
                "Content-Length",
                str(len(CAPTURE_PAGE))
            )
            self.end_headers()
            self.wfile.write(CAPTURE_PAGE)

        def do_POST(self):
            if urlsplit(self.path).path != "/api/capture":
                self.send_error(404)
                return

            try:
                length = int(
                    self.headers.get("Content-Length", "0")
                )

                if not 0 < length <= 5_000_000:
                    raise ValueError("Invalid snapshot size")

                state = json.loads(
                    self.rfile.read(length)
                )

                if not isinstance(state, dict):
                    raise ValueError(
                        "Snapshot must be a dictionary"
                    )

                missing = REQUIRED_KEYS - state.keys()

                if missing:
                    raise ValueError(
                        f"Missing fields: {sorted(missing)}"
                    )

            except (ValueError, UnicodeDecodeError) as error:
                message = str(error).encode("utf-8")

                self.send_response(400)
                self.send_header(
                    "Content-Type",
                    "text/plain; charset=utf-8"
                )
                self.send_header(
                    "Content-Length",
                    str(len(message))
                )
                self.end_headers()
                self.wfile.write(message)
                return

            if responses.empty():
                responses.put(state)

            self.send_response(200)
            self.end_headers()

        def log_message(self, *_args):
            pass

    url = str(replay_id)

    if not url.startswith(("https://", "http://")):
        url = (
            "https://www.duelingbook.com/replay"
            f"?id={replay_id}"
        )

    with ThreadingHTTPServer(
        ("127.0.0.1", port),
        CaptureHandler
    ) as server:

        thread = threading.Thread(
            target=server.serve_forever,
            daemon=True
        )
        thread.start()

        try:
            print(f"Opening replay: {url}")
            print("Navigate manually through the replay.")
            print("Click Capture state when ready.")

            webbrowser.open(url, new=1)

            # Blocks until the capture button is clicked
            state = responses.get(timeout=timeout)

            print("Game state captured successfully!")

            return state

        except queue.Empty as error:
            raise TimeoutError(
                "No capture received before timeout"
            ) from error

        finally:
            server.shutdown()
            thread.join()
