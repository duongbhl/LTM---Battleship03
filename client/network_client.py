# client/network_client.py
import socket
import threading
import queue

class NetworkClient:
    def __init__(self, host="127.0.0.1", port=5050):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.sock_lock = threading.Lock()
        self.recv_queue = queue.Queue()
        self.alive = True
        self.on_disconnect = None                         

        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()

    def _recv_loop(self):
        buffer = ""
        try:
            while self.alive:
                data = self.sock.recv(4096)
                if not data:
                    self.alive = False
                    if self.on_disconnect:
                        self.on_disconnect()
                    break
                # print("RAW RECV:", repr(data.decode()))
                buffer += data.decode()
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        self.recv_queue.put(line)
        except OSError:
            self.alive = False

    def send(self, msg: str):
        if not self.alive:
            print("[NET] send skipped: not alive")
            return
        data = (msg + "\n").encode()
        print("[NET] SEND:", repr(msg))
        with self.sock_lock:
            try:
                self.sock.sendall(data)
            except OSError:
                print("[NET] send error:", e)
                self.alive = False

    def read_nowait(self):
        """Lấy 1 message nếu có, nếu không thì trả về None."""
        try:
            return self.recv_queue.get_nowait()
        except queue.Empty:
            return None

    def close(self):
        self.alive = False
        try:
            self.sock.close()
        except OSError:
            pass
