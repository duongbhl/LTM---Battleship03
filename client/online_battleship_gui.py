import pygame
from network_client import NetworkClient
from dotenv import load_dotenv
import os

load_dotenv() 


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

EMOTE_SIZE = 48
EMOTES = {
    "😂": pygame.transform.smoothscale(
        pygame.image.load("assets/emotes/joy.png").convert_alpha(),
        (EMOTE_SIZE, EMOTE_SIZE)
    ),
    "😡": pygame.transform.smoothscale(
        pygame.image.load("assets/emotes/angry.png").convert_alpha(),
        (EMOTE_SIZE, EMOTE_SIZE)
    ),
    "😭": pygame.transform.smoothscale(
        pygame.image.load("assets/emotes/cry.png").convert_alpha(),
        (EMOTE_SIZE, EMOTE_SIZE)
    ),
    "😱": pygame.transform.smoothscale(
        pygame.image.load("assets/emotes/scream.png").convert_alpha(),
        (EMOTE_SIZE, EMOTE_SIZE)
    ),
    "🤔": pygame.transform.smoothscale(
        pygame.image.load("assets/emotes/thinking.png").convert_alpha(),
        (EMOTE_SIZE, EMOTE_SIZE)
    ),
    "🥱": pygame.transform.smoothscale(
        pygame.image.load("assets/emotes/yawn.png").convert_alpha(),
        (EMOTE_SIZE, EMOTE_SIZE)
    ),
    "😴": pygame.transform.smoothscale(
        pygame.image.load("assets/emotes/sleep.png").convert_alpha(),
        (EMOTE_SIZE, EMOTE_SIZE)
    ),
    "👍": pygame.transform.smoothscale(
        pygame.image.load("assets/emotes/thumbs_up.png").convert_alpha(),
        (EMOTE_SIZE, EMOTE_SIZE)
    ),
    "👎": pygame.transform.smoothscale(
        pygame.image.load("assets/emotes/thumbs_down.png").convert_alpha(),
        (EMOTE_SIZE, EMOTE_SIZE)
    ),
    "🏳️": pygame.transform.smoothscale(
        pygame.image.load("assets/emotes/white_flag.png").convert_alpha(),
        (EMOTE_SIZE, EMOTE_SIZE)
    ),
}

is_spectator = False

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

def wrap_text(text, font, max_width):
    words = text.split(" ")
    lines = []
    cur = ""

    for w in words:
        test = cur + (" " if cur else "") + w
        if font.size(test)[0] <= max_width:
            cur = test
        else:
            lines.append(cur)
            cur = w

    if cur:
        lines.append(cur)
    return lines

def render_scrolled(font, text, max_width, color):
    surf = font.render(text, True, color)
    while surf.get_width() > max_width:
        text = text[1:]
        surf = font.render(text, True, color)
    return surf


def run_online_game(net, username, mode, send_find_match:bool = True):
    global is_spectator
    sent_find_match = False

    is_spectator = (mode=="spectator")
    
    if mode == "spectator":
        phase = "spectating"
        message = "Waiting for game data..."
    else:
        phase = "queue"
        message = "Waiting for opponent..."
        if send_find_match and not sent_find_match:
            print("[CLIENT] SEND FIND_MATCH")
            net.send(f"FIND_MATCH|{username}|{mode}")
            sent_find_match = True

    
    my_elo = "?"
    opponent_elo = "?"

    # phase = "queue"
    message_color = TEXT
    if mode != "spectator":
        message = "Waiting for opponent..."
    else:
        message = "Waiting for game data..."

    
    # Normal matchmaking flow: client asks server to find a match.
    # Some flows (e.g. friend challenge accepted) already have a session created
    # on the server; in that case we only wait for MATCH_FOUND.
    # queue_started_at is managed by QUEUED / MATCH_FOUND messages below


    opponent = "???"
    my_turn = False
    TURN_TIME = 45
    turn_started_at = None


    my_board = ["U"] * 100
    
    enemy_board = ["U"] * 100

    # NEW — ships from server
    my_ships = ["0"] * 100
    spec_ships_p1 = ["0"] * 100
    spec_ships_p2 = ["0"] * 100
    show_my_ships = False

    result = None
    opponent_dc = False
    dc_countdown = 0
    dc_start_time = 0         
    
    # react
    my_react = None
    my_react_time = 0

    opp_react = None
    opp_react_time = 0

    REACT_DURATION = 3.0  # seconds

    # rematch
    rematch_requested = False
    rematch_prompt_open = False
    rematch_from_user = ""

    # react UI
    show_react_panel = False

    react_emojis = ["😂", "😡", "😭", "😱" ,"🤔","🥱","😴","👍", "👎","🏳️"]
    react_buttons = []

    # chat
    chat_active = False
    chat_input = ""
    chat_lines = []     # list[str]
    MAX_CHAT_LINES = 6

    INPUT_H = 36
    INPUT_Y = REAL_HEIGHT - 60 - 6 - INPUT_H
            
    # Queue timer
    queue_started_at = pygame.time.get_ticks()
    queue_elapsed = 0

    clock = pygame.time.Clock()

    exit_button = Button((REAL_WIDTH - 180, 20, 160, 40), "Back to Menu")
    show_button = Button((REAL_WIDTH - 360, 20, 160, 40), "Show Ships")
    rematch_button = Button((REAL_WIDTH - 540, 20, 160, 40), "Rematch")

    # Rematch prompt (modal) shown to the opponent when someone requests a rematch
    REMATCH_DIALOG_W, REMATCH_DIALOG_H = 520, 200
    rematch_dialog_x = (REAL_WIDTH - REMATCH_DIALOG_W) // 2
    rematch_dialog_y = (REAL_HEIGHT - REMATCH_DIALOG_H) // 2

    accept_rematch_button = Button(
        (rematch_dialog_x + 80, rematch_dialog_y + 120, 160, 50),
        "Accept",
        color=(80, 160, 90),
        hover=(110, 190, 120)
    )
    decline_rematch_button = Button(
        (rematch_dialog_x + REMATCH_DIALOG_W - 240, rematch_dialog_y + 120, 160, 50),
        "Decline",
        color=(200, 70, 70),
        hover=(230, 100, 100)
    )
    chat_button = Button(
        (20, REAL_HEIGHT - 60, 100, 40),
        "Chat"
    )

    react_button = Button(
        (130, REAL_HEIGHT - 60, 100, 40),
        "React"
    )
    PANEL_COLS = 5
    PANEL_ROWS = 2

    EMO_SIZE = 48          # kích thước icon
    EMO_GAP  = 12          # khoảng cách GIỮA các emoji

    CELL = EMO_SIZE + EMO_GAP
    PANEL_PADDING = 16

    panel_w = PANEL_COLS * CELL + PANEL_PADDING * 2
    panel_h = PANEL_ROWS * CELL + PANEL_PADDING * 2

    panel_x = 20
    panel_y = REAL_HEIGHT - panel_h - 90   # đẩy panel lên cao hơn


    for idx, emo in enumerate(react_emojis):
        row = idx // PANEL_COLS
        col = idx % PANEL_COLS

        rect = pygame.Rect(
            panel_x + PANEL_PADDING + col * CELL,
            panel_y + PANEL_PADDING + row * CELL,
            EMO_SIZE + 8,
            EMO_SIZE + 8
        )
        react_buttons.append({"emoji": emo, "rect": rect})




    running = True
    game_session_ended = False
    while running:
        mouse_pos = pygame.mouse.get_pos()

        # RECEIVE MESSAGES
        if  True:
            msg = net.read_nowait()
            if msg:
                for line in msg.split("\n"):
                    line = line.strip()
                    if not line:
                        continue

                    print("[CLIENT PARSED LINE]", line)
                    parts = line.split("|")
                    cmd = parts[0]

                    if cmd == "QUEUED":
                        if phase != "queue":
                            continue
                        if phase == "queue":
                            message = "Waiting for opponent..."
                        if queue_started_at is None:
                            queue_started_at = pygame.time.get_ticks()
                    elif cmd == "SPECTATOR_START":
                        phase = "playing"
                        my_turn = False
                        message = "Spectating match"
                        message_color = TEXT
                    elif cmd == "SPEC_BOARD":
                        if phase != "playing":
                            phase = "playing"
                            my_turn = False
                            message = "Spectating match"
                            message_color = TEXT
                        side = parts[1]
                        data = parts[2]

                        padded = list(data[:100])          # lấy tối đa 100
                        if len(padded) < 100:
                            padded += ["U"] * (100 - len(padded))

                        if side == "P1":
                            my_board = padded
                        elif side == "P2":
                            enemy_board = padded
                    elif cmd == "SPEC_SHIPS":
                        side = parts[1]
                        bitline = parts[2]

                        padded = list(bitline[:100])
                        if len(padded) < 100:
                            padded += ["0"] * (100 - len(padded))

                        if side == "P1":
                            spec_ships_p1 = padded
                        elif side == "P2":
                            spec_ships_p2 = padded

                    elif cmd == "SPEC_TURN":
                        if phase != "playing":
                            phase = "playing"
                            my_turn = False
                            message = "Spectating match"
                            message_color = TEXT
                    elif cmd == "SPEC_MOVE":
                        target = parts[1]   # P1/P2 = board bị bắn
                        x = int(parts[2]); y = int(parts[3])
                        idx = y * 10 + x
                        hit = parts[4]

                        board = my_board if target == "P1" else enemy_board
                        board[idx] = "H" if hit == "HIT" else "M"
                    
                    elif cmd == "SPEC_GAMEOVER":
                        winner = parts[1].split("=")[1]
                        reason = parts[2].split("=")[1]

                        phase = "gameover"
                        result = winner
                        message = f"Winner: {winner} ({reason})"
                        message_color = GOOD
                        game_session_ended = True
                        running = False
                    elif cmd == "MATCH_FOUND":
                        opponent_dc = False 
                        # (Re)start a match (also used for rematch)
                        phase = "playing"
                        result = None
                        opponent_dc = False
                        dc_countdown = 0
                        dc_start_time = 0

                        # reset boards/state
                        my_board = ["U"] * 100
                        enemy_board = ["U"] * 100
                        my_ships = ["0"] * 100
                        show_my_ships = False
    
                        my_react = None
                        opp_react = None
                        show_react_panel = False

                        chat_active = False
                        chat_input = ""
                        chat_lines = []

                        rematch_requested = False
                        rematch_prompt_open = False
                        rematch_from_user = ""

                        opponent = parts[1]
                        opponent_elo = parts[2]
                        my_turn = (parts[3] == "1")
                        message = "Your turn!" if my_turn else "Opponent's turn..."
                        message_color = GOOD if my_turn else TEXT
                    # stop/reset queue timer
                        send_find_match=True  # khoa match
                        queue_started_at = None
                        queue_elapsed = 0
                    elif cmd == "MY_SHIPS":
                        bitline = parts[1]
                        for i in range(min(100, len(bitline))):
                            my_ships[i] = bitline[i]

                    elif cmd == "YOUR_TURN":
                        opponent_dc = False 
                        my_turn = True
                        turn_started_at = pygame.time.get_ticks()
                        message = "Your turn"
                        message_color = GOOD
                    elif cmd == "OPPONENT_DISCONNECTED":
                        opponent_dc = True
                        dc_countdown = int(parts[1]) if len(parts) >= 2 else 10
                        dc_start_time = pygame.time.get_ticks()
                        message = f"Opponent disconnected. Auto-forfeit in {dc_countdown}s"
                        message_color = BAD                                                                                                                     
                    elif cmd == "OPPONENT_TURN":
                        opponent_dc = False 
                        my_turn = False
                        turn_started_at = pygame.time.get_ticks()
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

                        hit_result = parts[3]
                        status = parts[4].split("=")[-1]

                        if hit_result == "HIT":
                            my_board[idx] = "H"

                            if status == "SUNK":
                                ship_cells = parts[5] if len(parts) >= 6 else ""
                                for pos in ship_cells.split(","):
                                    if pos.isdigit():
                                        my_board[int(pos)] = "S"
                        else:
                            my_board[idx] = "M"  

                    elif cmd == "MY_REACT":
                        emoji = parts[1]
                        my_react = emoji
                        my_react_time = pygame.time.get_ticks()

                    elif cmd == "OPPONENT_REACT":
                        emoji = parts[1]
                        opp_react = emoji
                        opp_react_time = pygame.time.get_ticks()

                    elif cmd == "CHAT":
                        sender = parts[1]
                        text = parts[2]
                        chat_lines.append(f"[{sender}]: {text}")
                        if len(chat_lines) > MAX_CHAT_LINES:
                            chat_lines.pop(0)

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
                                
                            
                            
                            game_session_ended = True
                            # running = False                                       
    
                    elif cmd == "REMATCH":
                    # Server notifies that someone requested a rematch
                        who = parts[1] if len(parts) >= 2 else ""
                        if who == username:
                            message = "Rematch requested. Waiting for opponent..."
                            message_color = TEXT
                            rematch_requested = True
                        else:
                            rematch_from_user = who
                            rematch_prompt_open = True
                            message = f"{who} wants a rematch!"
                            message_color = TEXT

                    elif cmd == "REMATCH_ACCEPTED":
                        who = parts[1] if len(parts) >= 2 else ""
                        rematch_prompt_open = False
                        rematch_requested = True
                        if who == username:
                            message = "You accepted the rematch. Starting..."
                        else:
                            message = f"{who} accepted the rematch. Starting..."
                            message_color = TEXT

                    elif cmd == "REMATCH_DECLINED":
                        who = parts[1] if len(parts) >= 2 else ""
                        rematch_prompt_open = False
                        rematch_requested = False
                        if who == username:
                            message = "You declined the rematch."
                        else:
                            message = f"{who} declined the rematch."
                            message_color = TEXT
                            msg = net.read_nowait()






        # QUEUE TIMER
        if phase.startswith("queue") and queue_started_at:
            queue_elapsed = (pygame.time.get_ticks() - queue_started_at) // 1000

        # EVENTS
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                # ESC behaves like a context-aware "back".
                if phase in ("queue_wait_send", "queue"):
                    net.send("CANCEL_QUEUE")
                    running = False
                elif phase == "playing":
                    net.send(f"SURRENDER|{username}")
                    phase = "gameover"
                    # result = "LOSE"
                    result = None
                    message = "You surrendered!"
                    message_color = BAD
                elif phase == "gameover":
                    running = False

            elif ev.type == pygame.KEYDOWN and chat_active:
                if ev.key == pygame.K_RETURN:
                    if chat_input.strip():
                        net.send(f"CHAT|{chat_input.strip()}")
                    chat_input = ""
                    chat_active = False

                elif ev.key == pygame.K_BACKSPACE:
                    chat_input = chat_input[:-1]

                else:
                    if len(chat_input) < 80:
                        chat_input += ev.unicode

            elif ev.type == pygame.MOUSEMOTION:
                # hover cho 2 nút
                exit_button.update_hover(mouse_pos)
                if phase in ("playing", "gameover"):
                    show_button.update_hover(mouse_pos)
                    chat_button.update_hover(mouse_pos)
                    react_button.update_hover(mouse_pos)
                    if phase == "gameover":
                        rematch_button.update_hover(mouse_pos)
                        if rematch_prompt_open:
                            accept_rematch_button.update_hover(mouse_pos)
                            decline_rematch_button.update_hover(mouse_pos)
                else:
                    show_button.is_hover = False

            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if exit_button.clicked(ev):
                    # --- Not in game yet → Back to menu ---
                    if phase in ("queue_wait_send", "queue"):
                        net.send("LEAVE_QUEUE")
                        net.send("CANCEL_QUEUE")
                        running = False

                    # --- In match → Surrender ---
                    elif phase == "playing":
                        net.send(f"SURRENDER|{username}")
                        phase = "gameover"
                        # result = "LOSE"
                        result = None
                        message = "You surrendered!"
                        message_color = BAD

                    # --- After match → Back to menu ---
                    elif phase == "gameover":
                        net.send("LEAVE_GAME")
                        game_session_ended = True
                        running = False

                # Rematch prompt response (accept/decline)
                if phase == "gameover" and rematch_prompt_open:
                    if accept_rematch_button.clicked(ev):
                        net.send("REMATCH_ACCEPT")
                        rematch_prompt_open = False
                        rematch_requested = True
                        message = "You accepted the rematch. Starting..."
                        message_color = TEXT
                    elif decline_rematch_button.clicked(ev):
                        net.send("REMATCH_DECLINE")
                        rematch_prompt_open = False
                        rematch_requested = False
                        message = "You declined the rematch."
                        message_color = TEXT

                # Rematch request (only when no pending prompt)
                if (phase == "gameover" and rematch_button.clicked(ev)
                        and not rematch_requested and not rematch_prompt_open):
                    net.send("REMATCH")
                    rematch_requested = True
                    message = "Rematch requested. Waiting for opponent..."
                    message_color = TEXT

                if phase == "playing":
                    if chat_button.clicked(ev):
                        chat_active = True

                    elif react_button.clicked(ev):
                        show_react_panel = not show_react_panel
                
                if show_react_panel:
                    for r in react_buttons:
                        if r["rect"].collidepoint(ev.pos):
                            emoji = r["emoji"]
                            net.send(f"REACT|{emoji}")

                            show_react_panel = False
                            break


                if phase in ("playing", "gameover") and show_button.clicked(ev):
                    if is_spectator:
                        turn_text = "Spectating"
                    show_my_ships = not show_my_ships

                if phase == "playing" and my_turn:
                    if is_spectator:
                        continue  # spectators cannot make moves
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
              
        if phase == "playing" and turn_started_at:
            elapsed = (pygame.time.get_ticks() - turn_started_at) / 1000
            remain = max(0, TURN_TIME - int(elapsed))

            col = GOOD if remain > 10 else BAD
            timer_text = f"Time left: {remain}s"
            timer_surf = font_text.render(timer_text, True, col)

            # đặt countdown NGAY DƯỚI dòng TURN, center theo trục màn hình
            timer_y = turn_y + 32
            SCREEN.blit(
                timer_surf,
                timer_surf.get_rect(center=(REAL_WIDTH // 2, timer_y))
            )

        if phase.startswith("queue") and queue_started_at:
            t = f"Queue time: {queue_elapsed:02d}s"
            SCREEN.blit(font_small.render(t, True, TEXT),
                        (SIDE_PADDING, TOP_BANNER_HEIGHT + 75))

        if phase in ("playing", "gameover"):
            # draw my board
            draw_grid(my_board, LEFT_GRID_X, GRID_Y, "Your board")
            # draw enemy board
            draw_grid(enemy_board, RIGHT_GRID_X, GRID_Y, "Enemy board")

            # SHOW SHIPS
            if show_my_ships:
                if is_spectator:
                    # P1 ships (left board)
                    for i in range(100):
                        if spec_ships_p1[i] == "1":
                            r = i // 10
                            c = i % 10
                            rx = LEFT_GRID_X + c * GRID_SIZE
                            ry = GRID_Y + r * GRID_SIZE
                            pygame.draw.rect(SCREEN, SHIP_COLOR,
                                 (rx, ry, GRID_SIZE, GRID_SIZE), 0)

                    # P2 ships (right board)
                    for i in range(100):
                        if spec_ships_p2[i] == "1":
                            r = i // 10
                            c = i % 10
                            rx = RIGHT_GRID_X + c * GRID_SIZE
                            ry = GRID_Y + r * GRID_SIZE
                            pygame.draw.rect(SCREEN, SHIP_COLOR,
                                 (rx, ry, GRID_SIZE, GRID_SIZE), 0)
                else:
                    for i in range(100):
                        if my_ships[i] == "1":   
                            r = i // 10
                            c = i % 10
                            rx = LEFT_GRID_X + c * GRID_SIZE
                            ry = GRID_Y + r * GRID_SIZE
                            pygame.draw.rect(SCREEN, SHIP_COLOR,
                                         (rx, ry, GRID_SIZE, GRID_SIZE), 0)

            

            # ---- CHAT BOX ----
            CHAT_W = 360
            CHAT_X = LEFT_GRID_X

            CHAT_TOP_Y = GRID_Y + 8 * GRID_SIZE
            CHAT_BOTTOM_Y = GRID_Y + 10 * GRID_SIZE

            CHAT_Y = CHAT_TOP_Y
            CHAT_H = CHAT_BOTTOM_Y - CHAT_TOP_Y

            TOP_PADDING_CHAT = 8

            padding = 8
            line_h = font_small.get_height() + 2

            chat_bg = pygame.Surface((CHAT_W, CHAT_H), pygame.SRCALPHA)
            chat_bg.fill((0, 0, 0, 64))  # r,g,b,opacity
            SCREEN.blit(chat_bg, (CHAT_X, CHAT_Y))

            y = CHAT_Y + CHAT_H - padding - TOP_PADDING_CHAT

            # duyệt chat từ mới nhất
            for line in reversed(chat_lines):
                wrapped = wrap_text(line, font_small, CHAT_W - 16)

                for w in reversed(wrapped):
                    y -= line_h
                    if y < CHAT_Y + TOP_PADDING_CHAT:
                        break

                    # text chính
                    surf = font_small.render(w, True, TEXT)
                    SCREEN.blit(surf, (CHAT_X + 8, y))

            
            if chat_active:
                input_w = CHAT_W
                input_h = INPUT_H
                input_x = CHAT_X
                input_y = INPUT_Y

                pygame.draw.rect(
                    SCREEN, (40, 50, 70),
                    (input_x, input_y, input_w, input_h),
                    border_radius=8
                )

                display_text = chat_input + "|"
                txt = render_scrolled(
                    font_text,
                    display_text,
                    input_w - 16,
                    WHITE
                )
                SCREEN.blit(txt, (input_x + 8, input_y + 6))


        else:
            if phase.startswith("queue"):
                center_msg = "Finding opponent..."
            elif phase == "spectating":
                center_msg = "Watching match..."
            else:
                center_msg = "Connecting..."
            SCREEN.blit(font_title.render(center_msg, True, (200, 200, 255)),
                        (REAL_WIDTH//2 - 200, REAL_HEIGHT//2 - 40))

        if phase == "gameover":
            if is_spectator:
                rs = font_title.render(f"Winner: {result}", True, GOOD)
            else:
                col = GOOD if result == "WIN" else BAD
                rs = font_title.render(f"Result: {result}", True, col)
            SCREEN.blit(rs, rs.get_rect(center=(REAL_WIDTH//2,
                                                REAL_HEIGHT - BOTTOM_BANNER_HEIGHT//2)))
            # After game → Back to Menu
            exit_button.text = "Back to Menu"
            exit_button.color = (90, 110, 160)
            exit_button.hover = (120, 140, 190)
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

        if show_react_panel:
            pygame.draw.rect(
                SCREEN,
                (28, 38, 58),
                (panel_x - 4, panel_y - 4, panel_w + 8, panel_h + 8),
                border_radius=14
            )

            for r in react_buttons:
                if r["rect"].collidepoint(mouse_pos):
                    pygame.draw.rect(SCREEN, (90, 110, 140), r["rect"], border_radius=8)
                else:
                    pygame.draw.rect(SCREEN, (60, 70, 90), r["rect"], border_radius=8)
                SCREEN.blit(
                    EMOTES[r["emoji"]],
                    EMOTES[r["emoji"]].get_rect(center=r["rect"].center)
                )

        
        exit_button.draw(SCREEN)
        if phase in ("playing", "gameover"):
            show_button.draw(SCREEN)
            chat_button.draw(SCREEN)
            react_button.draw(SCREEN)

        if phase == "gameover":
            # Change button label after request
            rematch_button.text = "Requested" if rematch_requested else "Rematch"
            rematch_button.draw(SCREEN)

        # Draw opponent info
        info_y = TOP_BANNER_HEIGHT - 25
        info_surf = font_small.render(info, True, TEXT)
        info_x = SIDE_PADDING
        SCREEN.blit(info_surf, (info_x, info_y))

        now = pygame.time.get_ticks()

        # ---- MY REACT (left side) ----
        if my_react:
            elapsed = (now - my_react_time) / 1000
            if elapsed < REACT_DURATION:
                my_react_x = LEFT_GRID_X
                my_react_y = GRID_Y - 30 + 22

                SCREEN.blit(
                    EMOTES[my_react],
                    (my_react_x, my_react_y)
                )
            else:
                my_react = None


        # ---- OPPONENT REACT (right side) ----
        if opp_react:
            elapsed = (now - opp_react_time) / 1000
            if elapsed < REACT_DURATION:

                opp_react_x = RIGHT_GRID_X
                opp_react_y = GRID_Y - 30 + 22   

                SCREEN.blit(
                    EMOTES[opp_react],
                    (opp_react_x, opp_react_y)
                )


            else:
                opp_react = None


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

        # --- REMATCH PROMPT (modal) ---
        if phase == "gameover" and rematch_prompt_open:
            # Dark overlay
            overlay = pygame.Surface((REAL_WIDTH, REAL_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            SCREEN.blit(overlay, (0, 0))

            # Dialog box
            pygame.draw.rect(
                SCREEN,
                (40, 50, 70),
                (rematch_dialog_x, rematch_dialog_y, REMATCH_DIALOG_W, REMATCH_DIALOG_H),
                border_radius=12
            )
            pygame.draw.rect(
                SCREEN,
                WHITE,
                (rematch_dialog_x, rematch_dialog_y, REMATCH_DIALOG_W, REMATCH_DIALOG_H),
                2,
                border_radius=12
            )

            title_txt = font_text.render(f"{rematch_from_user} wants a rematch", True, TEXT)
            SCREEN.blit(
                title_txt,
                title_txt.get_rect(center=(REAL_WIDTH // 2, rematch_dialog_y + 55))
            )
            sub_txt = font_small.render("Do you accept?", True, TEXT)
            SCREEN.blit(
                sub_txt,
                sub_txt.get_rect(center=(REAL_WIDTH // 2, rematch_dialog_y + 90))
            )

            accept_rematch_button.draw(SCREEN)
            decline_rematch_button.draw(SCREEN)
                                                        
        pygame.display.flip()
        clock.tick(60)

    # NOTE: Do NOT close the shared session socket here.
    # The main menu and other features reuse this same connection.