# Runs one command with a static server for the repo on 127.0.0.1:8877 alive only for that command's lifetime
# (a daemon thread in this process: nothing outlives the call). For when tools/serve.js is not running.
#   python tools/with_server.py <command...>
import sys, os, threading, subprocess, mimetypes
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
mimetypes.add_type('model/gltf-binary', '.glb'); mimetypes.add_type('text/javascript', '.js'); mimetypes.add_type('text/javascript', '.mjs')
class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=ROOT, **k)
    def log_message(self, *a): pass
    def end_headers(self): self.send_header('Cache-Control', 'no-store'); super().end_headers()
srv = ThreadingHTTPServer(('127.0.0.1', 8877), H); srv.daemon_threads = True
threading.Thread(target=srv.serve_forever, daemon=True).start()
r = subprocess.run(sys.argv[1:]); srv.server_close(); sys.stdout.flush(); os._exit(r.returncode)
