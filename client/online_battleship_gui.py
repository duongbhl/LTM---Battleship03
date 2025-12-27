import pygame
from network_client import NetworkClient

pygame.init()
pygame.font.init()

SCREEN_INFO = pygame.display.Info()
REAL_WIDTH, REAL_HEIGHT = SCREEN_INFO.current_w, SCREEN_INFO.current_h
SCREEN = pygame.display.set_mode((REAL_WIDTH, REAL_HEIGHT), pygame.FULLSCREEN)

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
SUNK = (255, 60, 60)  
TEXT = (230, 230, 255)
TITLE = (120, 200, 255)
GOOD = (120, 255, 120)
BAD = (255, 120, 120)
SHIP_COLOR = (80, 180, 80)

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
            elif cell == "S":
                color = SUNK

            rx = x0 + c * GRID_SIZE
            ry = y0 + r * GRID_SIZE
            pygame.draw.rect(SCREEN, color, (rx, ry, GRID_SIZE, GRID_SIZE))
            pygame.draw.rect(SCREEN, WHITE, (rx, ry, GRID_SIZE, GRID_SIZE), 1)


def run_online_game(username, password, mode, host="10.242.244.3", port=5050): 
    net = NetworkClient(host, port)
    my_elo = "?"
    opponent_elo = "?"

    phase = "queue_wait_send"
    sent_find = False
    message = "Connecting to server..."
    message_color = TEXT

    opponent = "???"
    my_turn = False

    my_board = ["U"] * 100
    enemy_board = ["U"] * 100

    # NEW — ships from server
    my_ships = ["0"] * 100
    show_my_ships = False

    result = None
    opponent_dc = False
    dc_countdown = 0
    dc_start_time = 0                   

    # Queue timer
    queue_started_at = None
    queue_elapsed = 0

    clock = pygame.time.Clock()

    exit_button = Button((REAL_WIDTH - 180, 20, 160, 40), "Back to Menu")
    show_button = Button((REAL_WIDTH - 360, 20, 160, 40), "Show Ships")


    running = True
    while running:

        mouse_pos = pygame.mouse.get_pos()

        # RECEIVE MESSAGES
        msg = net.read_nowait()
        while msg is not None:
            for line in msg.split("\n"):
                line = line.strip()
                if not line:
                    continue

                print("[CLIENT PARSED LINE]", line)
                parts = line.split("|")
                cmd = parts[0]

                if cmd == "LOGIN_OK":
                    my_elo = parts[1]
                    phase = "queue_wait_send"
                    message = "Login OK. Searching..."
                    message_color = GOOD
                elif cmd == "LOGIN_FAIL":
                    phase = "error"
                    message = "Login failed"
                    continue
                elif cmd == "QUEUED":
                    phase = "queue"
                    message = "Waiting for opponent..."
                    if queue_started_at is None:
                        queue_started_at = pygame.time.get_ticks()

                elif cmd == "MATCH_FOUND":
                    opponent = parts[1]
                    opponent_elo = parts[2]
                    my_turn = (parts[3] == "1")
                    phase = "playing"
                    message = "Your turn!" if my_turn else "Opponent's turn..."
                    # stop/reset queue timer
                    queue_started_at = None
                    queue_elapsed = 0
                elif cmd == "MY_SHIPS":
                    bitline = parts[1]
                    for i in range(min(100, len(bitline))):
                        my_ships[i] = bitline[i]

                elif cmd == "YOUR_TURN":
                    my_turn = True
                    message = "Your turn"
                    message_color = GOOD
                elif cmd == "OPPONENT_DISCONNECTED":
                    opponent_dc = True
                    dc_countdown = int(parts[1]) if len(parts) >= 2 else 10
                    dc_start_time = pygame.time.get_ticks()
                    message = f"Opponent disconnected. Auto-forfeit in {dc_countdown}s"
                    message_color = BAD                                                                                                                        
                elif cmd == "OPPONENT_TURN":
                    my_turn = False
                    message = "Opponent's turn"
                    message_color = TEXT

                elif cmd == "MOVE_RESULT":
                    x = int(parts[1]); y = int(parts[2])
                    idx = y * 10 + x

                    hit_result = parts[3]
                    status = parts[4].split("=")[-1]

                    if hit_result == "HIT":
                        enemy_board[idx] = "H"   # tạm gán hit

                        # Nếu server báo tàu đã chìm
                        if status == "SUNK":
                            # server cần gửi thêm danh sách ô hull của tàu
                            ship_cells = parts[5] if len(parts) >= 6 else ""
                            # ví dụ ship_cells = "12,13,14,15"
                            for pos in ship_cells.split(","):
                                if pos.isdigit():
                                    enemy_board[int(pos)] = "S"
                    else:
                        enemy_board[idx] = "M"
                    if status == "WIN":
                        phase = "gameover"
                        result = "WIN"

                elif cmd == "OPPONENT_MOVE":
                    x = int(parts[1]); y = int(parts[2])
                    idx = y * 10 + x
                    my_board[idx] = "H" if parts[3] == "HIT" else "M"
                    status = parts[4].split("=")[-1]
                    if status == "LOSE":                                                                     
                        phase = "gameover"
                        result = "LOSE"
                elif cmd == "GAMEOVER":
                    if len(parts) >= 2:
                        phase = "gameover"
                        result = parts[1]
                        if result == "WIN":
                            message = "You win!"
                            message_color = GOOD
                        else:
                            message = "You lose!"
                            message_color = BAD                                       
            msg = net.read_nowait()

        # SEND FIND MATCH
        if phase == "queue_wait_send" and not sent_find:
            net.send(f"FIND_MATCH|{username}|{mode}")
            sent_find = True
            phase = "queue"
            queue_started_at = pygame.time.get_ticks()

        # QUEUE TIMER
        if phase.startswith("queue") and queue_started_at:
            queue_elapsed = (pygame.time.get_ticks() - queue_started_at) // 1000

        # EVENTS
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                running = False

            elif ev.type == pygame.MOUSEMOTION:
                # hover cho 2 nút
                exit_button.update_hover(mouse_pos)
                show_button.update_hover(mouse_pos)

            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if exit_button.clicked(ev):
                    # --- Not in game yet → Back to menu ---
                    if phase in ("queue_wait_send", "queue"):
                        running = False

                    # --- In match → Surrender ---
                    elif phase == "playing":
                        net.send(f"SURRENDER|{username}")
                        phase = "gameover"
                        result = "LOSE"
                        message = "You surrendered!"
                        message_color = BAD

                    # --- After match → Back to menu ---
                    elif phase == "gameover":
                        running = False

                if show_button.clicked(ev):
                    show_my_ships = not show_my_ships

                if phase == "playing" and my_turn:
                    click_x, click_y = ev.pos
                    gx, gy = RIGHT_GRID_X, GRID_Y
                    if gx <= mouse_pos[0] < gx + GRID_W and gy <= mouse_pos[1] < gy + GRID_H:
                        c = (mouse_pos[0] - gx) // GRID_SIZE
                        r = (mouse_pos[1] - gy) // GRID_SIZE
                        idx = r * 10 + c
                        if enemy_board[idx] == "U":
                            net.send(f"MOVE|{c}|{r}")
        # ----- DISCONNECT COUNTDOWN -----
        if opponent_dc:
            elapsed = (pygame.time.get_ticks() - dc_start_time) / 1000
            remaining = int(dc_countdown - elapsed)

            if remaining <= 0:
                # Opponent auto-forfeit
                phase = "gameover"
                result = "WIN"
                opponent_dc = False
                message = "Opponent forfeited!"
                message_color = GOOD
            else:
                message = f"Opponent disconnected. Auto-forfeit in {remaining}s"
                message_color = BAD
        # RENDER
        SCREEN.fill(BG)

        title = font_title.render("Battleship Online", True, TITLE)
        SCREEN.blit(title, title.get_rect(center=(REAL_WIDTH // 2, TOP_BANNER_HEIGHT // 2)))
        if phase in ("playing", "gameover"):
            turn_text = "Your turn" if my_turn else "Opponent turn"
            turn_color = GOOD if my_turn else BAD
            turn_surf = font_text.render(turn_text, True, turn_color)

            # place turn status horizontally centered, above the grids
            turn_y = GRID_Y - 30  # Adjust so it aligns cleanly above both boards
            SCREEN.blit(turn_surf, turn_surf.get_rect(center=(REAL_WIDTH // 2, turn_y)))

        info = f"You: {username} ({my_elo})"
        if phase in ("playing", "gameover"):
            info += f" | Opponent: {opponent} ({opponent_elo})"
        SCREEN.blit(font_small.render(info, True, TEXT), (SIDE_PADDING, TOP_BANNER_HEIGHT - 25))

        SCREEN.blit(font_text.render(message, True, message_color),
                    (SIDE_PADDING, TOP_BANNER_HEIGHT + 40))

        if phase.startswith("queue") and queue_started_at:
            t = f"Queue time: {queue_elapsed:02d}s"
            SCREEN.blit(font_small.render(t, True, TEXT),
                        (SIDE_PADDING, TOP_BANNER_HEIGHT + 75))

        if phase in ("playing", "gameover"):
            # draw my board
            draw_grid(my_board, LEFT_GRID_X, GRID_Y, "Your board")

            # SHOW SHIPS
            if show_my_ships:
                for i in range(100):
                    if my_ships[i] == "1":   
                        r = i // 10
                        c = i % 10
                        rx = LEFT_GRID_X + c * GRID_SIZE
                        ry = GRID_Y + r * GRID_SIZE
                        pygame.draw.rect(SCREEN, SHIP_COLOR,
                                         (rx, ry, GRID_SIZE, GRID_SIZE), 0)

            draw_grid(enemy_board, RIGHT_GRID_X, GRID_Y, "Enemy board")

        else:
            center_msg = "Finding opponent..." if phase.startswith("queue") else "Connecting..."
            SCREEN.blit(font_title.render(center_msg, True, (200, 200, 255)),
                        (REAL_WIDTH//2 - 200, REAL_HEIGHT//2 - 40))

        if phase == "gameover":
            col = GOOD if result == "WIN" else BAD
            rs = font_title.render(f"Result: {result}", True, col)
            SCREEN.blit(rs, rs.get_rect(center=(REAL_WIDTH//2,
                                                REAL_HEIGHT - BOTTOM_BANNER_HEIGHT//2)))
        exit_button.update_hover(mouse_pos)

        if phase in ("queue_wait_send", "queue"):
            # Not in game yet → Back to Menu
            exit_button.text = "Back to Menu"
            exit_button.color = (90, 110, 160)
            exit_button.hover = (120, 140, 190)

        elif phase == "playing":
            # In game → Surrender
            exit_button.text = "Surrender"
            exit_button.color = (200, 70, 70)
            exit_button.hover = (230, 100, 100)

        elif phase == "gameover":
            # After game → Back to Menu
            exit_button.text = "Back to Menu"
            exit_button.color = (90, 110, 160)
            exit_button.hover = (120, 140, 190)

        exit_button.draw(SCREEN)
        show_button.draw(SCREEN)

        # Draw opponent info
        info_y = TOP_BANNER_HEIGHT - 25
        info_surf = font_small.render(info, True, TEXT)
        info_x = SIDE_PADDING
        SCREEN.blit(info_surf, (info_x, info_y))

        # Draw disconnect countdown 
        if opponent_dc:
            elapsed = (pygame.time.get_ticks() - dc_start_time) / 1000
            remaining = int(dc_countdown - elapsed)
            dc_text = f"Opponent disconnected. Auto-forfeit in {remaining}s"
            dc_surf = font_small.render(dc_text, True, BAD)

            SCREEN.blit(
                dc_surf,
                (info_x + info_surf.get_width() + 20, info_y)  # 20px to the right
            )
                                                        
        pygame.display.flip()
        clock.tick(60)

    net.close()