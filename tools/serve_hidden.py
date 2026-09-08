# Start tools/serve.js on :8877 with no console window and no parent tie (Windows). Idempotent:
# does nothing if the port already answers.   python tools/serve_hidden.py [port]
import subprocess, sys, socket, os, time
port = int(sys.argv[1]) if len(sys.argv) > 1 else 8877
def up():
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.5): return True
    except OSError: return False
if up(): print('already up on', port); sys.exit(0)
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
flags = 0x08000000 | 0x00000008   # CREATE_NO_WINDOW | DETACHED_PROCESS
subprocess.Popen(['node', os.path.join(root, 'tools', 'serve.js'), '--port', str(port)], cwd=root, creationflags=flags, close_fds=True,
                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
for _ in range(20):
    time.sleep(0.25)
    if up(): print('up on', port); sys.exit(0)
print('did not come up'); sys.exit(1)
