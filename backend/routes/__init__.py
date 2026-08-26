import json
import time
from http.server import SimpleHTTPRequestHandler
from urllib.parse import urlparse


def create_web_handler(frontend_dir, training_state, state_lock,
                       stop_requested, training_started_at,
                       start_training, latest_frame, frame_condition):
    class WebHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=frontend_dir, **kwargs)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/stream":
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    while True:
                        with frame_condition:
                            frame_condition.wait(timeout=1)
                            frame = latest_frame()
                        if frame is None:
                            continue
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n")
                        self.wfile.write(frame)
                        self.wfile.write(b"\r\n")
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return

            if path == "/api/status":
                with state_lock:
                    payload = dict(training_state)
                if payload["running"] and training_started_at():
                    payload["elapsed"] = time.monotonic() - training_started_at()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())
                return

            super().do_GET()

        def do_POST(self):
            path = urlparse(self.path).path
            if path == "/api/start":
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                target = max(1, int(body.get("target", 10)))
                start_training(target)
                self.send_response(202)
            elif path == "/api/stop":
                stop_requested.set()
                with state_lock:
                    training_state["running"] = False
                    training_state["status"] = "RUN STOPPED"
                self.send_response(200)
            else:
                self.send_response(404)
            self.end_headers()

    return WebHandler
