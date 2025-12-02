# client/online_battleship_gui.py
import pygame
from network_client import NetworkClient

pygame.init()
pygame.font.init()

SCREEN_INFO = pygame.display.Info()
REAL_WIDTH, REAL_HEIGHT = SCREEN_INFO.current_w, SCREEN_INFO.current_h
SCREEN = pygame.display.set_mode((REAL_WIDTH, REAL_HEIGHT), pygame.FULLSCREEN)

# layout
SIDE_PADDING = 30
TOP_BANNER_HEIGHT = 80
BOTTOM_BANNER_HEIGHT = 140

GRID_GAP = 50
GRID_SIZE = min((REAL_WIDTH - 2 * SIDE_PADDING - GRID_GAP) // 20,
                (REAL_HEIGHT - TOP_BANNER_HEIGHT - BOTTOM_BANNER_HEIGHT) // 10)
if GRID_SIZE < 20:
    GRID_SIZE = 20

GRID_W = GRID_SIZE * 10
GRID_H = GRID_SIZE * 10

LEFT_GRID_X = SIDE_PADDING
RIGHT_GRID_X = REAL_WIDTH - SIDE_PADDING - GRID_W
GRID_Y = (REAL_HEIGHT - GRID_H) // 2

BG = (30, 35, 50)
WHITE = (245, 245, 245)
UNKNOWN = (70, 80, 90)
MISS = (60, 130, 200)
HIT = (240, 170, 60)
TEXT = (230, 230, 255)
TITLE = (120, 200, 255)
GOOD = (120, 255, 120)
BAD = (255, 120, 120)

font_title = pygame.font.SysFont("arial", 40, bold=True)
font_text = pygame.font.SysFont("arial", 24)
font_small = pygame.font.SysFont("arial", 20)


class Button:
    def __init__(self, rect, text, font=font_text,
                 color=(90, 110, 160), hover=(120, 140, 190)):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.color = color
        self.hover = hover
        self.is_hover = False

    def draw(self, surf):
        c = self.hover if self.is_hover else self.color
        pygame.draw.rect(surf, c, self.rect, border_radius=8)
        t = self.font.render(self.text, True, WHITE)
        surf.blit(t, t.get_rect(center=self.rect.center))

    def update_hover(self, pos):
        self.is_hover = self.rect.collidepoint(pos)

    def clicked(self, ev):
        return ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.is_hover


def draw_grid(board, x0, y0, title_text):
    pygame.draw.rect(SCREEN, WHITE, (x0-2, y0-2, GRID_W+4, GRID_H+4), 2, border_radius=4)
    title_surf = font_small.render(title_text, True, TEXT)
    SCREEN.blit(title_surf, (x0, y0 - 30))

    for r in range(10):
        for c in range(10):
            cell = board[r*10 + c]
            color = UNKNOWN
            if cell == "M":
                color = MISS
            elif cell == "H":
                color = HIT

            rx = x0 + c * GRID_SIZE
            ry = y0 + r * GRID_SIZE
            pygame.draw.rect(SCREEN, color, (rx, ry, GRID_SIZE, GRID_SIZE))
            pygame.draw.rect(SCREEN, WHITE, (rx, ry, GRID_SIZE, GRID_SIZE), 1)


def run_online_game(username, password, mode, host="127.0.0.1", port=5050):
    net = NetworkClient(host, port)

    # GAME STATE
    phase = "queue_wait_send"       # login → queue_wait_send → queue → playing → gameover
    sent_find = False          # chỉ gửi FIND_MATCH 1 lần
    message = "Connecting to server..."
    message_color = TEXT
    opponent = "???"
    my_turn = False
    my_board = ["U"] * 100
    enemy_board = ["U"] * 100
    result = None

    

    clock = pygame.time.Clock()
    exit_button = Button((REAL_WIDTH - 180, 20, 160, 40), "Back to Menu")

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()

        # ----- RECEIVE MESSAGES -----
        msg = net.read_nowait()
        while msg is not None:
            print("[CLIENT RECV]", msg)
            parts = msg.split("|")
            cmd = parts[0]

            if cmd == "LOGIN_OK":
                message = "Login OK. Searching for match..."
                message_color = GOOD
                phase = "queue_wait_send"   # CHUYỂN QUA TRẠNG THÁI CHỜ GỬI 
            
            elif cmd == "LOGIN_FAIL":
                phase = "error"
                message = "Login failed"
                continue


            elif cmd == "QUEUED":
                message = "Waiting for opponent..."
                message_color = (180, 180, 255)
                phase = "queue"

            elif cmd == "MATCH_FOUND":
                if len(parts) >= 3:
                    opponent = parts[1]
                    my_turn = parts[2] == "1"
                    phase = "playing"
                    message = f"Matched with {opponent}. " + ("Your turn!" if my_turn else "Opponent's turn...")
                    message_color = GOOD

            elif cmd == "YOUR_TURN":
                my_turn = True
                message = "Your turn!"
                message_color = GOOD

            elif cmd == "OPPONENT_TURN":
                my_turn = False
                message = "Opponent's turn..."
                message_color = TEXT

            elif cmd == "MOVE_RESULT":
                if len(parts) >= 5:
                    x = int(parts[1])
                    y = int(parts[2])
                    idx = y * 10 + x
                    enemy_board[idx] = "H" if parts[3] == "HIT" else "M"
                    status = parts[4].split("=")[-1]
                    if status == "WIN":
                        phase = "gameover"
                        result = "WIN"

            elif cmd == "OPPONENT_MOVE":
                if len(parts) >= 5:
                    x = int(parts[1])
                    y = int(parts[2])
                    idx = y * 10 + x
                    my_board[idx] = "H" if parts[3] == "HIT" else "M"
                    status = parts[4].split("=")[-1]
                    if status == "LOSE":
                        phase = "gameover"
                        result = "LOSE"

            msg = net.read_nowait()

        # ----- SEND FIND_MATCH (CHUẨN 100%) -----
        if phase == "queue_wait_send" and not sent_find:
            net.send(f"FIND_MATCH|{username}|{mode}")
            sent_find = True
            phase = "queue"

        # ----- EVENTS -----
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                running = False
            elif ev.type == pygame.MOUSEMOTION:
                exit_button.update_hover(mouse_pos)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if exit_button.clicked(ev):
                    running = False

                # TRONG TRẬN BẮN
                if phase == "playing" and my_turn:
                    gx, gy = RIGHT_GRID_X, GRID_Y
                    if gx <= mouse_pos[0] < gx + GRID_W and gy <= mouse_pos[1] < gy + GRID_H:
                        c = (mouse_pos[0] - gx) // GRID_SIZE
                        r = (mouse_pos[1] - gy) // GRID_SIZE
                        idx = r * 10 + c
                        if enemy_board[idx] == "U":
                            net.send(f"MOVE|{c}|{r}")

        # ----- RENDER -----
        SCREEN.fill(BG)

        title_surf = font_title.render("Battleship Online", True, TITLE)
        SCREEN.blit(title_surf, title_surf.get_rect(center=(REAL_WIDTH//2, TOP_BANNER_HEIGHT//2)))

        info = f"You: {username}"
        if phase in ("playing", "gameover"):
            info += f" | Opponent: {opponent}"
        SCREEN.blit(font_small.render(info, True, TEXT), (SIDE_PADDING, TOP_BANNER_HEIGHT + 10))

        if message:
            SCREEN.blit(font_text.render(message, True, message_color), (SIDE_PADDING, TOP_BANNER_HEIGHT + 40))

        # Board
        if phase in ("playing", "gameover"):
            draw_grid(my_board, LEFT_GRID_X, GRID_Y, "Your board (opponent shots)")
            draw_grid(enemy_board, RIGHT_GRID_X, GRID_Y, "Enemy board (your shots)" + (" - YOUR TURN" if my_turn else ""))
        else:
            center_msg = "Finding opponent..." if phase.startswith("queue") else "Connecting to server..."
            SCREEN.blit(font_title.render(center_msg, True, (200, 200, 255)),
                        (REAL_WIDTH//2 - 200, REAL_HEIGHT//2 - 40))

        # Game over
        if phase == "gameover" and result:
            col = GOOD if result == "WIN" else BAD
            rs = font_title.render(f"Result: {result}", True, col)
            SCREEN.blit(rs, rs.get_rect(center=(REAL_WIDTH//2, REAL_HEIGHT - BOTTOM_BANNER_HEIGHT//2)))

        exit_button.update_hover(mouse_pos)
        exit_button.draw(SCREEN)

        pygame.display.flip()
        clock.tick(60)

    net.close()
