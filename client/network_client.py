# client/network_client.py
import socket
import threading
import queue
from dotenv import load_dotenv
import os

load_dotenv() 


class NetworkClient:
    def __init__(self, host="127.0.0.1", port=5050): 
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.connect((host, port))
        self.sock_lock = threading.Lock()
        self.recv_queue = queue.Queue()
        self.alive = True
        self.on_disconnect = None                         
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()
        self.sock.setblocking(True)

    def _recv_loop(self):
        buffer = ""
        try:
            while self.alive:
                try:
                    data = self.sock.recv(4096)
                except socket.timeout:
                    continue
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
            except OSError as e:
                print("[NET] send error:", e)
                self.alive = False

    def read_nowait(self):
        """Lấy 1 message nếu có, nếu không thì trả về None."""
        try:
            return self.recv_queue.get_nowait()
        except queue.Empty:
            return None

    def push_front(self, msg: str):
        """Đưa 1 message trở lại *đầu* hàng đợi recv.

        Dùng trong trường hợp một màn hình (menu) đã đọc mất message quan trọng
        (ví dụ MATCH_FOUND) nhưng muốn nhường lại cho màn hình gameplay xử lý
        theo đúng thứ tự.
        """
        if msg is None:
            return
        # queue.Queue dùng deque nội bộ, có mutex sẵn.
        with self.recv_queue.mutex:
            self.recv_queue.queue.appendleft(msg)

    def close(self):
        self.alive = False
        try:
            self.sock.close()
        except OSError:
            pass

    @classmethod
    def from_socket(cls, sock):
        obj = cls.__new__(cls)

        obj.sock = sock
        obj.sock.settimeout(None)
        obj.sock.setblocking(True)
        obj.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        obj.sock_lock = threading.Lock()
        obj.recv_queue = queue.Queue()
        obj.alive = True
        obj.on_disconnect = None
        obj._recv_thread = threading.Thread(
            target=obj._recv_loop,
            daemon=True
        )
        obj._recv_thread.start()

        return obj

