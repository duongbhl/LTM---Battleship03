import pygame
import socket
import time
from network_client import NetworkClient
from dotenv import load_dotenv
import os

load_dotenv() 

pygame.init()
pygame.font.init()

MENU_SCREEN_INFO = pygame.display.Info()
MENU_WIDTH, MENU_HEIGHT = MENU_SCREEN_INFO.current_w, MENU_SCREEN_INFO.current_h
SCREEN = pygame.display.set_mode((MENU_WIDTH, MENU_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Battleship - Main Menu")

# Colors
BG_COLOR = (25, 35, 45)
TEXT_COLOR = (240, 248, 255)
BUTTON_TEXT_COLOR = (255, 255, 255)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER_COLOR = (100, 160, 210)
TITLE_COLOR = (100, 200, 255)
EXIT_BUTTON_COLOR = (200, 70, 70)
EXIT_BUTTON_HOVER_COLOR = (230, 100, 100)
SUCCESS_COLOR = (100, 255, 100)
ERROR_COLOR = (255, 100, 100)
LOGOUT_BUTTON_COLOR = (180, 130, 70)
LOGOUT_BUTTON_HOVER_COLOR = (210, 160, 100)
WHITE = (255, 255, 255)

# Font sizes
title_font_size = int(MENU_HEIGHT * 0.08)
button_font_size = int(MENU_HEIGHT * 0.04)
small_font_size = int(MENU_HEIGHT * 0.03)

font_title = pygame.font.SysFont("arial", title_font_size, bold=True)
font_button = pygame.font.SysFont("arial", button_font_size)
font_small = pygame.font.SysFont("arial", small_font_size)

def render_scrolled(font, text, max_width, color):
    surf = font.render(text, True, color)
    while surf.get_width() > max_width:
        text = text[1:]
        surf = font.render(text, True, color)
    return surf


# GLOBAL SESSION MANAGEMENT
current_user = None 
current_password = None  # giữ password tạm trong session để login socket gameplay
is_logged_in = False
session_sock = None

online_users = []
online_popup_open = False
last_online_fetch = 0

# ----- FRIEND SYSTEM STATE -----
friend_invites = []   # list[str]  user gửi lời mời
friend_popup_open = False

# ----- FRIEND SEARCH STATE -----
friend_search_text = ""
friend_search_active = False

# ----- FRIEND NOTIFY -----
friend_notify = None        # str
friend_notify_time = 0      # timestamp
FRIEND_NOTIFY_DURATION = 3  # seconds

# ----- FRIEND NOTIFICATION ICON -----
friend_notify_icon_flash = False

# ----- SEARCH STATUS MESSAGE -----
search_status_text = None
search_status_color = None
search_status_time = 0
SEARCH_STATUS_DURATION = 3

# ----- FRIEND CHALLENGE (ELO) STATE -----
challenge_requests = []         # list[str] - users who challenged you
challenge_popup_open = False

challenge_status_text = None
challenge_status_color = None
challenge_status_time = 0
CHALLENGE_STATUS_DURATION = 3

# ----- CHALLENGE DECLINED POPUP -----
challenge_decline_popup_open = False
challenge_decline_popup_by = ""   # username who declined your challenge

title_y_pos = int(MENU_HEIGHT * 0.20)

class Button:
    def __init__(self, rect, text, base_font=font_button, color=BUTTON_COLOR, hover_color=BUTTON_HOVER_COLOR):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.hovered = False
        self.font = base_font
        self.color = color
        self.hover_color = hover_color

    def draw(self, surface):
        current_color = self.hover_color if self.hovered else self.color
        pygame.draw.rect(surface, current_color, self.rect, border_radius=10)
        txt_surface = self.font.render(self.text, True, BUTTON_TEXT_COLOR)
        text_rect = txt_surface.get_rect(center=self.rect.center)
        surface.blit(txt_surface, text_rect)

    def is_hovered(self, pos):
        self.hovered = self.rect.collidepoint(pos)
        return self.hovered

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hovered


def launch_game(mode, send_find_match: bool = True):
    print("DEBUG: launch_game() called")   # PRINT 1

    from online_battleship_gui import run_online_game
    print("DEBUG: imported online_battleship_gui")  # PRINT 2

    global SCREEN, current_user, current_password

    print("DEBUG: current_user =", current_user)    # PRINT 3
    print("DEBUG: current_pass =", current_password)    # PRINT 3

    run_online_game(session_sock, current_user, mode, send_find_match=send_find_match)
    print("DEBUG: returned from run_online_game")   # PRINT 4


def send_auth_request(command, username, password):
    """
    Gửi request đăng nhập/đăng ký đến server C
    Returns: (success: bool, message: str)
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(("127.0.0.1", 5050)) 
        
        request = f"{command}|{username}|{password}\n"
        sock.sendall(request.encode())

        response = sock.recv(1024).decode()


        
        if "|" in response:
            status, message = response.split("|", 1)
            if status == "LOGIN_OK":
                sock.settimeout(None) 
                sock.setblocking(True)
                return True, sock
            elif status == "REGISTER_SUCCESS":
                return True, message
            else:  # ERROR
                return False, message
        else:
            return False, response
    
    except socket.timeout:
        return False, "Connection timeout. Is server running?"
    except ConnectionRefusedError:
        return False, "Cannot connect to server. Please start server first!"
    except Exception as e:
        return False, f"Error: {str(e)}"


def login_screen():
    """Màn hình đăng nhập"""
    global current_user,current_password,is_logged_in, session_sock

    # register inputs
    input_w = int(MENU_WIDTH * 0.40)
    input_h = int(MENU_HEIGHT * 0.10) 
    center_x = (MENU_WIDTH - input_w) // 2
    spacing = int(MENU_HEIGHT * 0.04)

    # positions aligned with register_screen
    user_top = MENU_HEIGHT//2 - 80
    pass_top = user_top + input_h + spacing

    BASE_Y = MENU_HEIGHT//2 - 220   

    input_box_user = pygame.Rect(center_x, BASE_Y, input_w, input_h)
    input_box_pass = pygame.Rect(center_x, BASE_Y + input_h + spacing, input_w, input_h)


    # buttons
    button_h = 70
    button_w = input_w // 2 - 10   # chia ô input thành 2 nút 
    gap = 20                       # khoảng cách giữa 2 nút

    row_y = input_box_pass.bottom + spacing   # đặt nút ngay dưới ô password

    # Cao bằng ô input
    button_h = input_h

    # Bo 2 nút vừa đúng chiều rộng = input_w
    button_w = input_w // 2 - 10
    row_y = input_box_pass.bottom + spacing   # chỉnh vị trí cao thấp 

    btn_login = Button(
        (center_x, row_y, button_w, button_h),
        "Login"
    )

    btn_register = Button(
        (center_x + button_w + gap, row_y, button_w, button_h),
        "Register"
    )

    back_y = row_y + button_h + spacing   

    btn_back = Button(
        (center_x, back_y, input_w, input_h),   
        "Back",
        color=EXIT_BUTTON_COLOR,
        hover_color=EXIT_BUTTON_HOVER_COLOR
    )

    username = ""
    password = ""
    active_user = True
    active_pass = False
    message = ""
    message_color = ERROR_COLOR
    clock = pygame.time.Clock()

    while True:
        SCREEN.fill((30, 30, 50))
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False  # back to pre-login

                if active_user:
                    if event.key == pygame.K_BACKSPACE:
                        username = username[:-1]
                    elif event.key in (pygame.K_RETURN, pygame.K_TAB):
                        active_user = False
                        active_pass = True
                    else:
                        if event.unicode and event.unicode.isprintable():
                            username += event.unicode


                elif active_pass:
                    if event.key == pygame.K_BACKSPACE:
                        password = password[:-1]
                    elif event.key == pygame.K_TAB:
                        active_pass = False
                        active_user = True
                    elif event.key == pygame.K_RETURN:
                        if username and password:
                            message = "Connecting to server..."
                            message_color = TEXT_COLOR
                            pygame.display.flip()

                            success, result = send_auth_request("LOGIN", username, password)
                            if success:
                                session_sock = NetworkClient.from_socket(result)  
                                current_user = username
                                current_password = password
                                is_logged_in = True
                                SCREEN.fill((30, 30, 50))
                                success_surf = font_title.render(f"Welcome, {username}!", True, SUCCESS_COLOR)
                                SCREEN.blit(success_surf, success_surf.get_rect(center=(MENU_WIDTH//2, MENU_HEIGHT//2)))
                                pygame.display.flip()
                                pygame.time.wait(1500)
                                return True
                            else:
                                message = result
                                message_color = ERROR_COLOR
                    else:
                        if event.unicode and event.unicode.isprintable():
                            password += event.unicode


            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box_user.collidepoint(event.pos):
                    active_user, active_pass = True, False
                elif input_box_pass.collidepoint(event.pos):
                    active_user, active_pass = False, True
                else:
                    active_user, active_pass = False, False

                if btn_login.is_clicked(event):
                    if not username or not password:
                        message = "Please enter both username and password"
                        message_color = ERROR_COLOR
                    else:
                        message = "Connecting to server..."
                        message_color = TEXT_COLOR
                        pygame.display.flip()

                        success, result = send_auth_request("LOGIN", username, password)
                        if success:
                            session_sock = NetworkClient.from_socket(result)
                            current_user = username
                            current_password = password
                            is_logged_in = True
                            SCREEN.fill((30, 30, 50))
                            success_surf = font_title.render(f"Welcome, {username}!", True, SUCCESS_COLOR)
                            SCREEN.blit(success_surf, success_surf.get_rect(center=(MENU_WIDTH//2, MENU_HEIGHT//2)))
                            pygame.display.flip()
                            pygame.time.wait(1500)
                            return True
                        else:
                            message = result
                            message_color = ERROR_COLOR

                if btn_register.is_clicked(event):
                    if register_screen():  # nếu register thành công
                        message = "Account created! Please login."
                        message_color = SUCCESS_COLOR
                        username = ""
                        password = ""

                if btn_back.is_clicked(event):
                    return False

        # Draw UI
        title_surf = font_title.render("LOGIN", True, TITLE_COLOR)
        title_rect = title_surf.get_rect(center=(MENU_WIDTH//2, int(MENU_HEIGHT * 0.20)))
        SCREEN.blit(title_surf, title_rect)

        # Username box
        color_user = (100, 120, 180) if active_user else (60, 70, 90)
        pygame.draw.rect(SCREEN, color_user, input_box_user, 0, 10)
        pygame.draw.rect(SCREEN, (150, 150, 200) if active_user else (100, 100, 120), input_box_user, 3, 10)
        user_display = username if username else "Username"
        if username:
            user_text_color = TEXT_COLOR
        else:
            user_text_color = (200, 200, 220) if active_user else (120, 120, 140)
        user_surf = render_scrolled(font_button, user_display, input_box_user.width - 30, user_text_color)
        SCREEN.blit(user_surf, (input_box_user.x + 15, input_box_user.y + (input_h - user_surf.get_height())//2))

        # Password box
        color_pass = (100, 120, 180) if active_pass else (60, 70, 90)
        pygame.draw.rect(SCREEN, color_pass, input_box_pass, 0, 10)
        pygame.draw.rect(SCREEN, (150, 150, 200) if active_pass else (100, 100, 120), input_box_pass, 3, 10)
        pass_display = "•" * len(password) if password else "Password"
        if password:
            pass_text_color = TEXT_COLOR
        else:
            pass_text_color = (200, 200, 220) if active_pass else (120, 120, 140)

        pass_surf = render_scrolled(font_button, pass_display, input_box_pass.width - 30, pass_text_color)
        SCREEN.blit(pass_surf, (input_box_pass.x + 15, input_box_pass.y + (input_h - pass_surf.get_height())//2))

        # Message
        if message:
            msg_surf = font_small.render(message, True, message_color)
            msg_rect = msg_surf.get_rect(center=(MENU_WIDTH//2, pass_top + input_h*2 + spacing*2))
            SCREEN.blit(msg_surf, msg_rect)

        # Buttons
        btn_login.is_hovered(mouse_pos)
        btn_register.is_hovered(mouse_pos)
        btn_back.is_hovered(mouse_pos)
        btn_login.draw(SCREEN)
        btn_register.draw(SCREEN)
        btn_back.draw(SCREEN)

        # Hints
        hint_surf = font_small.render("TAB to switch | ENTER to login | ESC to go back", True, (150, 150, 170))
        hint_rect = hint_surf.get_rect(center=(MENU_WIDTH//2, MENU_HEIGHT - 50))
        SCREEN.blit(hint_surf, hint_rect)

        pygame.display.flip()
        clock.tick(60)


def register_screen():
    """Màn hình đăng ký - Returns True nếu thành công"""
    input_w = int(MENU_WIDTH * 0.40)
    input_h = int(MENU_HEIGHT * 0.10) 
    center_x = (MENU_WIDTH - input_w) // 2
    spacing = int(MENU_HEIGHT * 0.04)

    BASE_Y = MENU_HEIGHT//2 - 220   # chỉnh lên/xuống 

    # 3 ô input: username, password, confirm
    input_box_user    = pygame.Rect(center_x, BASE_Y, input_w, input_h)
    input_box_pass    = pygame.Rect(center_x, BASE_Y + (input_h + spacing), input_w, input_h)
    input_box_confirm = pygame.Rect(center_x, BASE_Y + (input_h + spacing)*2, input_w, input_h)

    register_y = input_box_confirm.bottom + spacing
    button_h = input_h
    button_w = input_w // 2 - 10
    gap = 20

    row_y = input_box_confirm.bottom + spacing  

    btn_register = Button(
        (center_x, row_y, button_w, button_h),
        "Register"
    )

    btn_back = Button(
        (center_x + button_w + gap, row_y, button_w, button_h),
        "Back",
        color=EXIT_BUTTON_COLOR,
        hover_color=EXIT_BUTTON_HOVER_COLOR
    )

    # vị trí để vẽ message
    msg_y = row_y + button_h + spacing


    username = ""
    password = ""
    confirm_password = ""
    active_user = True
    active_pass = False
    active_confirm = False

    message = ""
    message_color = ERROR_COLOR
    clock = pygame.time.Clock()

    while True:
        SCREEN.fill((40, 40, 60))
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False

                if active_user:
                    if event.key == pygame.K_BACKSPACE:
                        username = username[:-1]
                    elif event.key in (pygame.K_RETURN, pygame.K_TAB):
                        active_user = False
                        active_pass = True
                        active_confirm = False
                    else:
                        if event.unicode and event.unicode.isprintable():
                            username += event.unicode


                elif active_pass:
                    if event.key == pygame.K_BACKSPACE:
                        password = password[:-1]
                    elif event.key in (pygame.K_RETURN, pygame.K_TAB):
                        # chuyển qua confirm nếu Tab / Enter
                        active_pass = False
                        active_confirm = True
                    else:
                        if event.unicode and event.unicode.isprintable():
                            password += event.unicode


                elif active_confirm:
                    if event.key == pygame.K_BACKSPACE:
                        confirm_password = confirm_password[:-1]
                    elif event.key == pygame.K_TAB:
                        # quay vòng về user
                        active_confirm = False
                        active_user = True
                    elif event.key == pygame.K_RETURN:
                        # khi Enter ở ô confirm => thực hiện đăng ký (với kiểm tra)
                        if not username or not password or not confirm_password:
                            message = "Please fill all fields"
                            message_color = ERROR_COLOR
                        elif password != confirm_password:
                            message = "Passwords do not match!"
                            message_color = ERROR_COLOR
                        else:
                            message = "Creating account..."
                            message_color = TEXT_COLOR
                            pygame.display.flip()
                            success, msg = send_auth_request("REGISTER", username, password)
                            if success:
                                SCREEN.fill((40, 40, 60))
                                success_surf = font_title.render("Account Created!", True, SUCCESS_COLOR)
                                hint_surf = font_button.render("Returning to login...", True, TEXT_COLOR)
                                SCREEN.blit(success_surf, success_surf.get_rect(center=(MENU_WIDTH//2, MENU_HEIGHT//2 - 30)))
                                SCREEN.blit(hint_surf, hint_surf.get_rect(center=(MENU_WIDTH//2, MENU_HEIGHT//2 + 40)))
                                pygame.display.flip()
                                pygame.time.wait(2000)
                                return True
                            else:
                                message = msg
                                message_color = ERROR_COLOR
                    else:
                        if event.unicode and event.unicode.isprintable():
                            confirm_password += event.unicode


            if event.type == pygame.MOUSEBUTTONDOWN:
                # set active field theo click
                if input_box_user.collidepoint(event.pos):
                    active_user, active_pass, active_confirm = True, False, False
                elif input_box_pass.collidepoint(event.pos):
                    active_user, active_pass, active_confirm = False, True, False
                elif input_box_confirm.collidepoint(event.pos):
                    active_user, active_pass, active_confirm = False, False, True
                else:
                    active_user, active_pass, active_confirm = False, False, False

                # nút register
                if btn_register.is_clicked(event):
                    if not username or not password or not confirm_password:
                        message = "Please fill all fields"
                        message_color = ERROR_COLOR
                    elif password != confirm_password:
                        message = "Passwords do not match!"
                        message_color = ERROR_COLOR
                    else:
                        message = "Creating account..."
                        message_color = TEXT_COLOR
                        pygame.display.flip()
                        success, msg = send_auth_request("REGISTER", username, password)
                        if success:
                            SCREEN.fill((40, 40, 60))
                            success_surf = font_title.render("Account Created!", True, SUCCESS_COLOR)
                            hint_surf = font_button.render("Returning to login...", True, TEXT_COLOR)
                            SCREEN.blit(success_surf, success_surf.get_rect(center=(MENU_WIDTH//2, MENU_HEIGHT//2 - 30)))
                            SCREEN.blit(hint_surf, hint_surf.get_rect(center=(MENU_WIDTH//2, MENU_HEIGHT//2 + 40)))
                            pygame.display.flip()
                            pygame.time.wait(2000)
                            return True

                if btn_back.is_clicked(event):
                    return False

        # ---------- DRAW UI ----------
        title_surf = font_title.render("REGISTER", True, TITLE_COLOR)
        title_rect = title_surf.get_rect(center=(MENU_WIDTH//2, int(MENU_HEIGHT * 0.20)))
        SCREEN.blit(title_surf, title_rect)

        # Username box
        color_user = (100, 120, 180) if active_user else (60, 70, 90)
        pygame.draw.rect(SCREEN, color_user, input_box_user, 0, 10)
        pygame.draw.rect(SCREEN, (150, 150, 200) if active_user else (100, 100, 120), input_box_user, 3, 10)
        user_display = username if username else "Username"
        if username:
            user_text_color = TEXT_COLOR
        else:
            user_text_color = (200, 200, 220) if active_user else (120, 120, 140)

        user_surf = render_scrolled(font_button, user_display, input_box_user.width - 30, user_text_color)
        SCREEN.blit(user_surf, (input_box_user.x + 15, input_box_user.y + (input_h - user_surf.get_height())//2))

        # Password box
        color_pass = (100, 120, 180) if active_pass else (60, 70, 90)
        pygame.draw.rect(SCREEN, color_pass, input_box_pass, 0, 10)
        pygame.draw.rect(SCREEN, (150, 150, 200) if active_pass else (100, 100, 120), input_box_pass, 3, 10)
        pass_display = "•" * len(password) if password else "Password"
        if password:
            pass_text_color = TEXT_COLOR
        else:
            pass_text_color = (200, 200, 220) if active_pass else (120, 120, 140)

        pass_surf = render_scrolled(font_button, pass_display, input_box_pass.width - 30, pass_text_color)
        SCREEN.blit(pass_surf, (input_box_pass.x + 15, input_box_pass.y + (input_h - pass_surf.get_height())//2))

        # Confirm password box
        color_confirm = (100, 120, 180) if active_confirm else (60, 70, 90)
        pygame.draw.rect(SCREEN, color_confirm, input_box_confirm, 0, 10)
        pygame.draw.rect(SCREEN, (150, 150, 200) if active_confirm else (100, 100, 120), input_box_confirm, 3, 10)
        confirm_display = "•" * len(confirm_password) if confirm_password else "Confirm Password"
        if confirm_password:
            confirm_color = TEXT_COLOR
        else:
            confirm_color = (200, 200, 220) if active_confirm else (120, 120, 140)

        confirm_surf = render_scrolled(font_button, confirm_display, input_box_confirm.width - 30, confirm_color)
        SCREEN.blit(confirm_surf, (input_box_confirm.x + 15, input_box_confirm.y + (input_h - confirm_surf.get_height())//2))

        # Message
        if message:
            msg_surf = font_small.render(message, True, message_color)
            msg_rect = msg_surf.get_rect(center=(MENU_WIDTH // 2, msg_y))
            SCREEN.blit(msg_surf, msg_rect)

        # Buttons
        btn_register.is_hovered(mouse_pos)
        btn_back.is_hovered(mouse_pos)
        btn_register.draw(SCREEN)
        btn_back.draw(SCREEN)

        # Hints
        hint_surf = font_small.render("TAB to switch | ENTER to register | ESC to go back", True, (150, 150, 170))
        SCREEN.blit(hint_surf, hint_surf.get_rect(center=(MENU_WIDTH//2, MENU_HEIGHT - 50)))

        pygame.display.flip()
        clock.tick(60)


def show_history(username):
    net = NetworkClient()
    net.send(f"GET_HISTORY|{username}")

    history = []   # mỗi phần tử: (date, result, opponent, elo)
    clock = pygame.time.Clock()
    running = True

    while running:
        # ---- HANDLE NETWORK ----
        msg = net.read_nowait()
        if msg:
            if msg == "HISTORY_END":
                # đã nhận xong lịch sử
                pass
            elif msg.startswith("HISTORY|"):
                parts = msg.split("|")
                if len(parts) >= 5:
                    date = parts[1]
                    result = parts[2]
                    opponent = parts[3]
                    elo = parts[4]
                    history.append((date, result, opponent, elo))

        # ---- EVENTS ----
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False

        # ---- RENDER ----
        SCREEN.fill((30, 30, 50))

        title = font_title.render("MATCH HISTORY", True, TITLE_COLOR)
        SCREEN.blit(title, title.get_rect(center=(MENU_WIDTH // 2, 80)))

        if not history:
            empty = font_small.render(
                "No match history found",
                True,
                (180, 180, 200)
            )
            SCREEN.blit(
                empty,
                empty.get_rect(center=(MENU_WIDTH // 2, MENU_HEIGHT // 2))
            )
        else:
            y = 160
            for date, result, opponent, elo in history[:10]:
                text = f"{date} | {result} vs {opponent} ({elo})"
                color = SUCCESS_COLOR if result == "WIN" else ERROR_COLOR
                line = font_small.render(text, True, color)
                SCREEN.blit(line, (200, y))
                y += 36

        hint = font_small.render(
            "Press ESC to return",
            True,
            (150, 150, 170)
        )
        SCREEN.blit(
            hint,
            hint.get_rect(center=(MENU_WIDTH // 2, MENU_HEIGHT - 50))
        )

        pygame.display.flip()
        clock.tick(60)

    net.close()


def friend_notifications_screen():
    global current_screen, friend_invites, session_sock

    clock = pygame.time.Clock()
    running = True

    # back button
    back_btn = Button(
        (30, MENU_HEIGHT - 80, 140, 44),
        "Back",
        color=(120, 120, 140),
        hover_color=(160, 160, 180)
    )

    while running:
        SCREEN.fill(BG_COLOR)
        mouse_pos = pygame.mouse.get_pos()

        # Title
        title = font_title.render("Friend Requests", True, TITLE_COLOR)
        SCREEN.blit(title, title.get_rect(center=(MENU_WIDTH // 2, 80)))

        # Content box
        box_w, box_h = 520, 360
        box_x = (MENU_WIDTH - box_w) // 2
        box_y = 140

        pygame.draw.rect(
            SCREEN, (40, 50, 70),
            (box_x, box_y, box_w, box_h),
            border_radius=14
        )
        pygame.draw.rect(
            SCREEN, (120, 150, 200),
            (box_x, box_y, box_w, box_h),
            2, border_radius=14
        )

        if not friend_invites:
            empty = font_small.render(
                "No pending friend requests",
                True, (160, 160, 180)
            )
            SCREEN.blit(
                empty,
                empty.get_rect(center=(MENU_WIDTH // 2, box_y + box_h // 2))
            )
        else:
            for i, sender in enumerate(friend_invites[:4]):
                y = box_y + 30 + i * 70

                txt = font_small.render(
                    f"{sender} wants to be your friend",
                    True, (200, 255, 200)
                )
                SCREEN.blit(txt, (box_x + 30, y))

                accept = Button(
                    (box_x + box_w - 260, y + 26, 100, 36),
                    "Accept",
                    color=(70, 160, 90),
                    hover_color=(100, 190, 120)
                )
                reject = Button(
                    (box_x + box_w - 140, y + 26, 100, 36),
                    "Reject",
                    color=(180, 80, 80),
                    hover_color=(220, 110, 110)
                )

                accept.is_hovered(mouse_pos)
                reject.is_hovered(mouse_pos)
                accept.draw(SCREEN)
                reject.draw(SCREEN)

                for event in pygame.event.get(pygame.MOUSEBUTTONDOWN):
                    if accept.is_clicked(event):
                        session_sock.send(
                            f"FRIEND_ACCEPT|{current_user}|{sender}"
                        )
                        friend_invites.remove(sender)
                        break

                    if reject.is_clicked(event):
                        session_sock.send(
                            f"FRIEND_REJECT|{current_user}|{sender}"
                        )
                        friend_invites.remove(sender)
                        break

        # Back button
        back_btn.is_hovered(mouse_pos)
        back_btn.draw(SCREEN)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            if back_btn.is_clicked(event):
                current_screen = "main"
                return

        pygame.display.flip()
        clock.tick(60)

def friends_online_screen():
    global online_users, session_sock, current_user
    global challenge_requests, challenge_popup_open
    global challenge_status_text, challenge_status_color, challenge_status_time
    global challenge_decline_popup_open, challenge_decline_popup_by

    clock = pygame.time.Clock()

    back_btn = Button(
        (30, MENU_HEIGHT - 80, 140, 44),
        "Back",
        color=(120, 120, 140),
        hover_color=(160, 160, 180)
    )

    # Challenge popup (modal)
    dialog_w, dialog_h = 560, 240
    dialog_x = (MENU_WIDTH - dialog_w) // 2
    dialog_y = (MENU_HEIGHT - dialog_h) // 2

    accept_btn = Button(
        (dialog_x + 70, dialog_y + 150, 180, 55),
        "Accept",
        base_font=font_small,
        color=(70, 160, 90),
        hover_color=(90, 190, 120)
    )
    decline_btn = Button(
        (dialog_x + dialog_w - 250, dialog_y + 150, 180, 55),
        "Decline",
        base_font=font_small,
        color=(200, 70, 70),
        hover_color=(230, 100, 100)
    )

    last_fetch = 0
    scroll_offset = 0
    running = True
    while running:
        SCREEN.fill(BG_COLOR)
        mouse_pos = pygame.mouse.get_pos()

        # ===== Socket receive (so invites & match start are handled even inside this screen) =====
        if session_sock:
            msg = session_sock.read_nowait()
            while msg:
                if msg.startswith("FRIENDS_ONLINE|"):
                    users = msg.split("|", 1)[1].strip(",")
                    online_users = users.split(",") if users else []

                elif msg.startswith("CHALLENGE_INVITE|"):
                    sender = msg.split("|", 1)[1]
                    if sender and sender not in challenge_requests:
                        challenge_requests.append(sender)
                    challenge_popup_open = True

                elif msg.startswith("CHALLENGE_SENT|"):
                    target = msg.split("|", 1)[1]
                    challenge_status_text = f"Challenge sent to {target}"
                    challenge_status_color = SUCCESS_COLOR
                    challenge_status_time = time.time()

                elif msg.startswith("CHALLENGE_DECLINED|"):
                    who = msg.split("|", 1)[1]
                    # If you are the challenger and the other side declines, show popup
                    if who and who != current_user:
                        challenge_decline_popup_open = True
                        challenge_decline_popup_by = who
                        challenge_status_text = None

                elif msg.startswith("CHALLENGE_CANCELLED|"):
                    who = msg.split("|", 1)[1]
                    # If the challenger cancels, remove it from pending list
                    if who in challenge_requests:
                        challenge_requests.remove(who)
                        if not challenge_requests:
                            challenge_popup_open = False
                            scroll_offset = 0

                    challenge_status_text = f"Challenge cancelled by {who}"
                    challenge_status_color = (220, 200, 80)
                    challenge_status_time = time.time()

                elif msg.startswith("MATCH_FOUND|"):
                    # A game has started (e.g. challenge accepted). Hand control to the game UI.
                    # Put back to FRONT so gameplay receives MATCH_FOUND before MY_SHIPS / YOUR_TURN
                    session_sock.push_front(msg)
                    challenge_popup_open = False
                    challenge_requests.clear()
                    launch_game("rank", send_find_match=False)
                    return

                else:
                    session_sock.recv_queue.put(msg)
                    break

                msg = session_sock.read_nowait()

        # ===== Periodically refresh friends online list =====
        now = time.time()
        if session_sock and current_user and now - last_fetch > 3:
            session_sock.send(f"GET_FRIENDS_ONLINE|{current_user}")
            last_fetch = now

        # ===== Layout =====
        title = font_title.render("FRIENDS ONLINE", True, TITLE_COLOR)
        SCREEN.blit(title, title.get_rect(center=(MENU_WIDTH // 2, 80)))

        box_w, box_h = 640, 500
        box_x = (MENU_WIDTH - box_w) // 2
        box_y = 140

        pygame.draw.rect(SCREEN, (40, 50, 70), (box_x, box_y, box_w, box_h), border_radius=14)
        pygame.draw.rect(SCREEN, (120, 150, 200), (box_x, box_y, box_w, box_h), 2, border_radius=14)

        # Status message (challenge sent/declined etc.)
        if challenge_status_text and time.time() - challenge_status_time < CHALLENGE_STATUS_DURATION:
            st = font_small.render(challenge_status_text, True, challenge_status_color)
            SCREEN.blit(st, (box_x + 30, box_y - 36))

        # Friends list + challenge buttons
        challenge_buttons = []  # list[(username, Button)]
        if not online_users:
            empty = font_small.render("No friends online", True, (160, 160, 180))
            SCREEN.blit(empty, empty.get_rect(center=(MENU_WIDTH // 2, box_y + box_h // 2)))
        else:
            LINE_H = 40
            ICON_R = 6

            y = box_y + 30
            for u in online_users[:10]:
                pygame.draw.circle(
                    SCREEN,
                    (120, 255, 120),           # xanh online
                    (box_x + 24, y + LINE_H//2),
                    ICON_R
                )
                name_surf = font_small.render(u, True, (230, 230, 255))
                SCREEN.blit(name_surf, (box_x + 40, y + 10))

                


                btn = Button(
                    (box_x + box_w - 190, y - 8, 160, 34),
                    "Challenge",
                    base_font=font_small,
                    color=(90, 110, 160),
                    hover_color=(120, 140, 190)
                )
                btn.is_hovered(mouse_pos)
                btn.draw(SCREEN)
                challenge_buttons.append((u, btn))

                y += LINE_H

        back_btn.is_hovered(mouse_pos)
        back_btn.draw(SCREEN)
        # ===== Challenge popup modal =====
        challenge_row_buttons = []  # list[(sender, accept_btn, decline_btn)]
        if challenge_popup_open and challenge_requests:
            overlay = pygame.Surface((MENU_WIDTH, MENU_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            SCREEN.blit(overlay, (0, 0))

            row_h = 52
            header_h = 92
            bottom_pad = 26
            dialog_w = 780
            max_h = MENU_HEIGHT - 120
            n = len(challenge_requests)
            dialog_h = min(max(260, header_h + bottom_pad + n * row_h), max_h)

            dialog_x = (MENU_WIDTH - dialog_w) // 2
            dialog_y = (MENU_HEIGHT - dialog_h) // 2

            pygame.draw.rect(SCREEN, (45, 55, 75), (dialog_x, dialog_y, dialog_w, dialog_h), border_radius=14)
            pygame.draw.rect(SCREEN, (120, 150, 200), (dialog_x, dialog_y, dialog_w, dialog_h), 2, border_radius=14)

            title2 = font_button.render("ELO Challenges", True, WHITE)
            SCREEN.blit(title2, title2.get_rect(center=(dialog_x + dialog_w // 2, dialog_y + 40)))

            msg2 = font_small.render("Accept / Decline each invite", True, (200, 200, 220))
            SCREEN.blit(msg2, msg2.get_rect(center=(dialog_x + dialog_w // 2, dialog_y + 76)))

            visible_rows = max(1, int((dialog_h - header_h - bottom_pad) // row_h))
            if scroll_offset > max(0, n - visible_rows):
                scroll_offset = max(0, n - visible_rows)

            start_i = scroll_offset
            end_i = min(n, start_i + visible_rows)

            if n > visible_rows:
                hint = font_small.render(f"Scroll: {start_i + 1}-{end_i} / {n}", True, (180, 180, 200))
                SCREEN.blit(hint, (dialog_x + 20, dialog_y + dialog_h - 28))

            y0 = dialog_y + header_h
            for idx in range(start_i, end_i):
                sender = challenge_requests[idx]
                y = y0 + (idx - start_i) * row_h

                line = font_small.render(sender, True, TEXT_COLOR)
                SCREEN.blit(line, (dialog_x + 30, y + 10))

                a_btn = Button(
                    (dialog_x + dialog_w - 330, y + 6, 140, 40),
                    "Accept",
                    base_font=font_small,
                    color=(70, 160, 90),
                    hover_color=(90, 190, 120)
                )
                d_btn = Button(
                    (dialog_x + dialog_w - 170, y + 6, 140, 40),
                    "Decline",
                    base_font=font_small,
                    color=(200, 70, 70),
                    hover_color=(230, 100, 100)
                )

                a_btn.is_hovered(mouse_pos)
                d_btn.is_hovered(mouse_pos)
                a_btn.draw(SCREEN)
                d_btn.draw(SCREEN)

                challenge_row_buttons.append((sender, a_btn, d_btn))

        # ===== Popup: Challenge declined (for challengers) =====
        declined_ok_btn = None
        if challenge_decline_popup_open and challenge_decline_popup_by:
            overlay = pygame.Surface((MENU_WIDTH, MENU_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            SCREEN.blit(overlay, (0, 0))

            pw, ph = 560, 220
            px = (MENU_WIDTH - pw) // 2
            py = (MENU_HEIGHT - ph) // 2

            pygame.draw.rect(SCREEN, (45, 55, 75), (px, py, pw, ph), border_radius=14)
            pygame.draw.rect(SCREEN, (120, 150, 200), (px, py, pw, ph), 2, border_radius=14)

            title = font_button.render("Th\xe1ch \u0111\u1ea5u", True, WHITE)
            SCREEN.blit(title, title.get_rect(center=(px + pw // 2, py + 40)))

            msg_txt = f"{challenge_decline_popup_by} \u0111\xe3 t\u1eeb ch\u1ed1i l\u1eddi th\xe1ch \u0111\u1ea5u c\u1ee7a b\u1ea1n."
            msg_surf = font_small.render(msg_txt, True, (230, 230, 255))
            SCREEN.blit(msg_surf, msg_surf.get_rect(center=(px + pw // 2, py + 90)))

            declined_ok_btn = Button(
                (px + (pw - 180) // 2, py + 140, 180, 55),
                "OK",
                base_font=font_small
            )
            declined_ok_btn.is_hovered(mouse_pos)
            declined_ok_btn.draw(SCREEN)

        # ===== Events =====
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); exit()
            # ===== Declined popup is modal =====
            if challenge_decline_popup_open and challenge_decline_popup_by:
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    challenge_decline_popup_open = False
                    challenge_decline_popup_by = ""
                    continue

                if declined_ok_btn and declined_ok_btn.is_clicked(ev):
                    challenge_decline_popup_open = False
                    challenge_decline_popup_by = ""
                    continue

                # Block other input while popup is open
                continue
            # ===== Challenge popup is modal =====
            if challenge_popup_open and challenge_requests:
                # Mouse wheel scroll support
                if ev.type == pygame.MOUSEWHEEL:
                    if ev.y > 0:
                        scroll_offset = max(0, scroll_offset - 1)
                    elif ev.y < 0:
                        scroll_offset = min(max(0, len(challenge_requests) - 1), scroll_offset + 1)
                    continue

                if ev.type == pygame.MOUSEBUTTONDOWN:
                    if ev.button == 4:
                        scroll_offset = max(0, scroll_offset - 1)
                        continue
                    if ev.button == 5:
                        scroll_offset = min(max(0, len(challenge_requests) - 1), scroll_offset + 1)
                        continue

                # ESC declines all pending invites
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    if session_sock and current_user:
                        for sender in list(challenge_requests):
                            session_sock.send(f"CHALLENGE_DECLINE|{current_user}|{sender}")
                    challenge_requests.clear()
                    challenge_popup_open = False
                    scroll_offset = 0
                    continue

                handled = False
                for sender, a_btn, d_btn in challenge_row_buttons:
                    if a_btn.is_clicked(ev):
                        if session_sock and current_user:
                            session_sock.send(f"CHALLENGE_ACCEPT|{current_user}|{sender}")
                            # UI hint while waiting for MATCH_FOUND
                            challenge_status_text = f"\u0110\xe3 ch\u1ea5p nh\u1eadn {sender}. \u0110ang v\xe0o tr\u1eadn..."
                            challenge_status_color = SUCCESS_COLOR
                            challenge_status_time = time.time()
                        challenge_requests.clear()
                        challenge_popup_open = False
                        scroll_offset = 0
                        handled = True
                        break

                    if d_btn.is_clicked(ev):
                        if session_sock and current_user:
                            session_sock.send(f"CHALLENGE_DECLINE|{current_user}|{sender}")
                        if sender in challenge_requests:
                            challenge_requests.remove(sender)
                        if not challenge_requests:
                            challenge_popup_open = False
                            scroll_offset = 0
                        handled = True
                        break

                # Ignore other interactions while popup open
                continue

            # ESC without popup closes this screen
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                running = False

            # Normal interactions
            if back_btn.is_clicked(ev):
                running = False

            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for friend_name, btn in challenge_buttons:
                    if btn.is_clicked(ev):
                        if session_sock and current_user:
                            session_sock.send(f"CHALLENGE_ELO|{current_user}|{friend_name}")
                        break

        pygame.display.flip()
        clock.tick(60)


def pre_login_menu():
    """Menu trước khi đăng nhập: Login/Register + Exit"""
    button_width = int(MENU_WIDTH * 0.45)
    button_height = int(MENU_HEIGHT * 0.09)
    spacing = int(MENU_HEIGHT * 0.03)

    title_y_pos = int(MENU_HEIGHT * 0.20)
    start_y = title_y_pos + int(MENU_HEIGHT * 0.15)

    buttons = {
        "login": Button(
            ((MENU_WIDTH - button_width) // 2, start_y, button_width, button_height),
            "Login / Register"
        ),
        "exit": Button(
            ((MENU_WIDTH - button_width) // 2, start_y + (button_height + spacing), button_width, button_height),
            "Exit Game",
            color=EXIT_BUTTON_COLOR,
            hover_color=EXIT_BUTTON_HOVER_COLOR
        )
    }

    clock = pygame.time.Clock()
    running = True

    while running:
        SCREEN.fill(BG_COLOR)
        mouse_pos = pygame.mouse.get_pos()

        # Title
        title_surf = font_title.render("BATTLESHIP", True, TITLE_COLOR)
        title_rect = title_surf.get_rect(center=(MENU_WIDTH // 2, title_y_pos))
        SCREEN.blit(title_surf, title_rect)

        # Subtitle
        subtitle_surf = font_small.render("Please login to continue", True, TEXT_COLOR)
        subtitle_rect = subtitle_surf.get_rect(center=(MENU_WIDTH // 2, title_y_pos + 60))
        SCREEN.blit(subtitle_surf, subtitle_rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                exit()

            for key, btn in buttons.items():
                if btn.is_clicked(event):
                    if key == "login":
                        if login_screen():  # Nếu login thành công
                            return  # Chuyển sang main menu
                    elif key == "exit":
                        pygame.quit()
                        exit()

        for btn in buttons.values():
            btn.is_hovered(mouse_pos)
            btn.draw(SCREEN)

        pygame.display.flip()
        clock.tick(60)


def main_menu():
    global current_user, is_logged_in, session_sock
    global online_users, last_online_fetch
    global friend_invites
    global friend_search_text, friend_search_active
    global friend_notify, friend_notify_time
    global search_status_text, search_status_color, search_status_time
    global challenge_requests, challenge_popup_open
    global challenge_status_text, challenge_status_color, challenge_status_time
    global challenge_decline_popup_open, challenge_decline_popup_by

    clock = pygame.time.Clock()
    running = True

    # ================= MAIN BUTTONS =================
    button_width = int(MENU_WIDTH * 0.45)
    button_height = int(MENU_HEIGHT * 0.09)
    spacing = int(MENU_HEIGHT * 0.03)

    title_y = int(MENU_HEIGHT * 0.15)
    start_y = title_y + int(MENU_HEIGHT * 0.12)

    buttons = {
        "pvp_rank": Button(
            ((MENU_WIDTH - button_width) // 2, start_y, button_width, button_height),
            "PvP - Ranked (ELO)"
        ),
        "pvp_open": Button(
            ((MENU_WIDTH - button_width) // 2,
             start_y + (button_height + spacing),
             button_width, button_height),
            "PvP - Open"
        ),
        "logout": Button(
            ((MENU_WIDTH - button_width) // 2,
             start_y + (button_height + spacing) * 2,
             button_width, button_height),
            "Logout",
            color=LOGOUT_BUTTON_COLOR,
            hover_color=LOGOUT_BUTTON_HOVER_COLOR
        ),
        "exit": Button(
            ((MENU_WIDTH - button_width) // 2,
             start_y + (button_height + spacing) * 3,
             button_width, button_height),
            "Exit Game",
            color=EXIT_BUTTON_COLOR,
            hover_color=EXIT_BUTTON_HOVER_COLOR
        ),
        "history": Button(
            ((MENU_WIDTH - button_width) // 2,
             start_y + (button_height + spacing) * 4,
             button_width, button_height),
            "Match History"
        ),
    }

    # ================= FRIEND PANEL =================
    PANEL_X = MENU_WIDTH - 360
    PANEL_Y = 18
    PANEL_W = 340

    online_button = Button(
        rect=(PANEL_X, PANEL_Y, PANEL_W, 48),
        text="Friends Online: 0",
        color=(60, 160, 90),
        hover_color=(90, 190, 120)
    )

    INPUT_Y = PANEL_Y + 60
    input_rect = pygame.Rect(PANEL_X, INPUT_Y, 220, 36)
    send_rect  = pygame.Rect(PANEL_X + 230, INPUT_Y, 90, 36)

    notify_rect = pygame.Rect(20, 20, 44, 44)

    # ----- Challenge popup (modal) -----
    chall_w, chall_h = 560, 240
    chall_x = (MENU_WIDTH - chall_w) // 2
    chall_y = (MENU_HEIGHT - chall_h) // 2

    accept_challenge_btn = Button(
        (chall_x + 70, chall_y + 150, 180, 55),
        "Accept",
        base_font=font_small,
        color=(70, 160, 90),
        hover_color=(90, 190, 120)
    )
    decline_challenge_btn = Button(
        (chall_x + chall_w - 250, chall_y + 150, 180, 55),
        "Decline",
        base_font=font_small,
        color=(200, 70, 70),
        hover_color=(230, 100, 100)
    )

    # ================= LOOP =================
    scroll_offset = 0  # for challenge popup scrolling

    while running:
        SCREEN.fill(BG_COLOR)
        mouse_pos = pygame.mouse.get_pos()

        # ========== SOCKET RECEIVE ==========
        if session_sock:
            msg = session_sock.read_nowait()
            while msg:
                if msg.startswith("FRIENDS_ONLINE|"):
                    users = msg.split("|", 1)[1].strip(",")
                    online_users = users.split(",") if users else []
                    online_button.text = f"Friends Online: {len(online_users)}"

                elif msg.startswith("FRIEND_INVITES|"):
                    users = msg.split("|", 1)[1].strip(",")
                    for u in users.split(","):
                        if u and u not in friend_invites:
                            friend_invites.append(u)

                elif msg.startswith("FRIEND_ACCEPTED|"):
                    friend_notify = f"{msg.split('|',1)[1]} accepted your request"
                    friend_notify_time = time.time()

                elif msg.startswith("FRIEND_REJECTED|"):
                    friend_notify = f"{msg.split('|',1)[1]} rejected your request"
                    friend_notify_time = time.time()

                elif msg.startswith("CHALLENGE_INVITE|"):
                    sender = msg.split("|", 1)[1]
                    if sender and sender not in challenge_requests:
                        challenge_requests.append(sender)
                    challenge_popup_open = True

                elif msg.startswith("CHALLENGE_SENT|"):
                    target = msg.split("|", 1)[1]
                    challenge_status_text = f"Challenge sent to {target}"
                    challenge_status_color = SUCCESS_COLOR
                    challenge_status_time = time.time()

                elif msg.startswith("CHALLENGE_DECLINED|"):
                    who = msg.split("|", 1)[1]
                    # If you are the challenger and the other side declines, show popup
                    if who and who != current_user:
                        challenge_decline_popup_open = True
                        challenge_decline_popup_by = who
                        challenge_status_text = None

                elif msg.startswith("CHALLENGE_CANCELLED"):
                    # may be "CHALLENGE_CANCELLED" or "CHALLENGE_CANCELLED|user"
                    parts = msg.split("|", 1)
                    who = parts[1] if len(parts) > 1 else ""

                    # If the challenger cancels (and you are the target), remove it from pending list
                    if who and who in challenge_requests:
                        challenge_requests.remove(who)
                        if not challenge_requests:
                            challenge_popup_open = False
                            scroll_offset = 0

                    challenge_status_text = (f"Challenge cancelled by {who}" if who else "Challenge cancelled")
                    challenge_status_color = (220, 200, 80)
                    challenge_status_time = time.time()

                elif msg.startswith("MATCH_FOUND|"):
                    # A game has started (e.g. your challenge was accepted). Hand control to the game UI.
                    # Put back to FRONT so gameplay receives MATCH_FOUND before MY_SHIPS / YOUR_TURN
                    session_sock.push_front(msg)
                    challenge_popup_open = False
                    challenge_requests.clear()
                    launch_game("rank", send_find_match=False)
                    break

                elif msg.startswith("FRIEND_SENT|"):
                    target = msg.split("|", 1)[1]
                    search_status_text = f"Friend invited: {target}"
                    search_status_color = (120, 255, 120)
                    search_status_time = time.time()

                elif msg.startswith("ERROR|"):
                    search_status_text = msg.split("|", 1)[1]
                    search_status_color = (255, 120, 120)
                    search_status_time = time.time()

                else:
                    session_sock.recv_queue.put(msg)
                    break

                msg = session_sock.read_nowait()

        # Precompute challenge popup layout/buttons (used for both event handling and drawing)
        challenge_row_buttons = []  # list[(sender, accept_btn, decline_btn)]
        challenge_popup_layout = None
        if challenge_popup_open and challenge_requests:
            row_h = 52
            header_h = 92
            bottom_pad = 26
            pop_w = 780
            max_h = MENU_HEIGHT - 160

            n_inv = len(challenge_requests)
            pop_h = min(max(260, header_h + bottom_pad + n_inv * row_h), max_h)
            pop_x = (MENU_WIDTH - pop_w) // 2
            pop_y = (MENU_HEIGHT - pop_h) // 2

            visible_rows = max(1, int((pop_h - header_h - bottom_pad) // row_h))
            if scroll_offset > max(0, n_inv - visible_rows):
                scroll_offset = max(0, n_inv - visible_rows)

            start_i = scroll_offset
            end_i = min(n_inv, start_i + visible_rows)

            y0 = pop_y + header_h
            for idx in range(start_i, end_i):
                sender = challenge_requests[idx]
                y = y0 + (idx - start_i) * row_h

                a_btn = Button(
                    (pop_x + pop_w - 330, y + 6, 140, 40),
                    "Accept",
                    base_font=font_small,
                    color=(70, 160, 90),
                    hover_color=(90, 190, 120)
                )
                d_btn = Button(
                    (pop_x + pop_w - 170, y + 6, 140, 40),
                    "Decline",
                    base_font=font_small,
                    color=(200, 70, 70),
                    hover_color=(230, 100, 100)
                )
                a_btn.is_hovered(mouse_pos)
                d_btn.is_hovered(mouse_pos)
                challenge_row_buttons.append((sender, a_btn, d_btn))

            challenge_popup_layout = (pop_x, pop_y, pop_w, pop_h, header_h, bottom_pad, row_h, start_i, end_i, n_inv, visible_rows)

        # ========== TITLE ==========
        title = font_title.render("BATTLESHIP", True, TITLE_COLOR)
        SCREEN.blit(title, title.get_rect(center=(MENU_WIDTH // 2, title_y)))

        status = font_small.render(
            f"Logged in as: {current_user}", True, SUCCESS_COLOR
        )
        SCREEN.blit(
            status,
            status.get_rect(center=(MENU_WIDTH // 2, title_y + 60))
        )

        # ========== NOTIFICATION ICON ==========
        icon_color = (220, 200, 80) if friend_invites else (120, 120, 140)
        pygame.draw.circle(SCREEN, icon_color, notify_rect.center, 20)
        if friend_invites:
            pygame.draw.circle(
                SCREEN,
                (220, 60, 60),
                (notify_rect.right - 6, notify_rect.top + 6),
                10
            )
            num = font_small.render(str(len(friend_invites)), True, WHITE)
            SCREEN.blit(num, num.get_rect(center=(notify_rect.right - 6, notify_rect.top + 6)))

        # ========== FRIEND SEARCH ==========
        pygame.draw.rect(
            SCREEN,
            (50, 60, 80) if friend_search_active else (40, 50, 70),
            input_rect,
            border_radius=8
        )
        pygame.draw.rect(SCREEN, (120, 150, 200), input_rect, 2, border_radius=8)

        display_text = friend_search_text or "Search player"
        color = TEXT_COLOR if friend_search_text else (150, 150, 170)

        max_w = input_rect.width - 24   # padding trái + phải

        # Cắt text từ BÊN TRÁI cho tới khi vừa ô
        while font_small.size(display_text)[0] > max_w:
            display_text = display_text[1:]

        text_surf = font_small.render(display_text, True, color)
        text_rect = text_surf.get_rect(
            midleft=(input_rect.x + 12, input_rect.centery)
        )
        SCREEN.blit(text_surf, text_rect)


        pygame.draw.rect(SCREEN, (70, 160, 90), send_rect, border_radius=8)
        SCREEN.blit(
            font_small.render("Send", True, WHITE),
            font_small.render("Send", True, WHITE).get_rect(center=send_rect.center)
        )

        if search_status_text and time.time() - search_status_time < 3:
            SCREEN.blit(
                font_small.render(search_status_text, True, search_status_color),
                (input_rect.x, input_rect.bottom + 6))
        # Challenge status (sent/declined/cancelled)
        if challenge_status_text and time.time() - challenge_status_time < CHALLENGE_STATUS_DURATION:
            st2 = font_small.render(challenge_status_text, True, challenge_status_color)
            SCREEN.blit(st2, (20, title_y_pos + 105))

        # Declined popup button (modal)
        declined_ok_btn = None
        if challenge_decline_popup_open and challenge_decline_popup_by:
            pw, ph = 560, 220
            px = (MENU_WIDTH - pw) // 2
            py = (MENU_HEIGHT - ph) // 2
            declined_ok_btn = Button(
                (px + (pw - 180) // 2, py + 140, 180, 55),
                "OK",
                base_font=font_small
            )
            declined_ok_btn.is_hovered(mouse_pos)

            

        # ========== EVENTS ==========
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); exit()
            # ===== Declined popup is modal =====
            if challenge_decline_popup_open and challenge_decline_popup_by:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    challenge_decline_popup_open = False
                    challenge_decline_popup_by = ""
                    continue

                if declined_ok_btn and declined_ok_btn.is_clicked(event):
                    challenge_decline_popup_open = False
                    challenge_decline_popup_by = ""
                    continue

                # Block other input while popup is open
                continue
            # ===== Challenge popup is modal (blocks the rest of the menu) =====
            if challenge_popup_open and challenge_requests:
                # Mouse wheel scroll support
                if event.type == pygame.MOUSEWHEEL:
                    if event.y > 0:
                        scroll_offset = max(0, scroll_offset - 1)
                    elif event.y < 0:
                        scroll_offset = min(max(0, len(challenge_requests) - 1), scroll_offset + 1)
                    continue

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 4:
                        scroll_offset = max(0, scroll_offset - 1)
                        continue
                    if event.button == 5:
                        scroll_offset = min(max(0, len(challenge_requests) - 1), scroll_offset + 1)
                        continue

                # ESC = Decline all pending invites
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if session_sock and current_user:
                        for sender in list(challenge_requests):
                            session_sock.send(f"CHALLENGE_DECLINE|{current_user}|{sender}")
                    challenge_requests.clear()
                    challenge_popup_open = False
                    scroll_offset = 0
                    continue
                # Handle Accept/Decline per-row
                handled = False
                for sender, a_btn, d_btn in challenge_row_buttons:
                    a_btn.is_hovered(mouse_pos)
                    d_btn.is_hovered(mouse_pos)

                    if a_btn.is_clicked(event):
                        if session_sock and current_user:
                            session_sock.send(f"CHALLENGE_ACCEPT|{current_user}|{sender}")
                            challenge_status_text = f"\u0110\xe3 ch\u1ea5p nh\u1eadn {sender}. \u0110ang v\xe0o tr\u1eadn..."
                            challenge_status_color = SUCCESS_COLOR
                            challenge_status_time = time.time()
                        challenge_requests.clear()
                        challenge_popup_open = False
                        scroll_offset = 0
                        handled = True
                        break

                    if d_btn.is_clicked(event):
                        if session_sock and current_user:
                            session_sock.send(f"CHALLENGE_DECLINE|{current_user}|{sender}")
                        if sender in challenge_requests:
                            challenge_requests.remove(sender)
                        if not challenge_requests:
                            challenge_popup_open = False
                            scroll_offset = 0
                        handled = True
                        break

                # Ignore other interactions while popup open
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    current_user = None
                    is_logged_in = False
                    return
                if friend_search_active:
                    if event.key == pygame.K_BACKSPACE:
                        friend_search_text = friend_search_text[:-1]
                    elif event.key == pygame.K_RETURN:
                        if friend_search_text.strip():
                            session_sock.send(f"FRIEND_REQUEST|{current_user}|{friend_search_text.strip()}")
                        friend_search_text = ""
                        friend_search_active = False
                    elif event.unicode.isprintable() and len(friend_search_text) < 20:
                        friend_search_text += event.unicode

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                friend_search_active = input_rect.collidepoint(event.pos)

                if send_rect.collidepoint(event.pos) and friend_search_text.strip():
                    session_sock.send(f"FRIEND_REQUEST|{current_user}|{friend_search_text.strip()}")
                    friend_search_text = ""
                    friend_search_active = False

                if notify_rect.collidepoint(event.pos):
                    friend_notifications_screen()

                if online_button.rect.collidepoint(event.pos):
                    friends_online_screen()

                for k, btn in buttons.items():
                    if btn.is_clicked(event):
                        if k == "pvp_rank":
                            launch_game("rank")
                        elif k == "pvp_open":
                            launch_game("open")
                        elif k == "history":
                            show_history(current_user)
                        elif k == "logout":
                            session_sock.send(f"LOGOUT|{current_user}")
                            session_sock.close()
                            return
                        elif k == "exit":
                            pygame.quit(); exit()

        # ========== DRAW ==========
        for btn in buttons.values():
            btn.is_hovered(mouse_pos)
            btn.draw(SCREEN)

        online_button.is_hovered(mouse_pos)
        online_button.draw(SCREEN)
        # ===== Challenge popup modal (draw last) =====
        if challenge_popup_open and challenge_requests and challenge_popup_layout:
            pop_x, pop_y, pop_w, pop_h, header_h, bottom_pad, row_h, start_i, end_i, n_inv, visible_rows = challenge_popup_layout

            overlay = pygame.Surface((MENU_WIDTH, MENU_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            SCREEN.blit(overlay, (0, 0))

            pygame.draw.rect(SCREEN, (45, 55, 75), (pop_x, pop_y, pop_w, pop_h), border_radius=14)
            pygame.draw.rect(SCREEN, (120, 150, 200), (pop_x, pop_y, pop_w, pop_h), 2, border_radius=14)

            t = font_button.render("ELO Challenges", True, WHITE)
            SCREEN.blit(t, t.get_rect(center=(pop_x + pop_w // 2, pop_y + 40)))

            m = font_small.render("Accept / Decline each invite", True, (200, 200, 220))
            SCREEN.blit(m, m.get_rect(center=(pop_x + pop_w // 2, pop_y + 76)))

            if n_inv > visible_rows:
                hint = font_small.render(f"Scroll: {start_i + 1}-{end_i} / {n_inv}", True, (180, 180, 200))
                SCREEN.blit(hint, (pop_x + 20, pop_y + pop_h - 28))

            y0 = pop_y + header_h
            for idx in range(start_i, end_i):
                sender = challenge_requests[idx]
                y = y0 + (idx - start_i) * row_h
                line = font_small.render(sender, True, TEXT_COLOR)
                SCREEN.blit(line, (pop_x + 30, y + 10))

            for _, a_btn, d_btn in challenge_row_buttons:
                a_btn.is_hovered(mouse_pos)
                d_btn.is_hovered(mouse_pos)
                a_btn.draw(SCREEN)
                d_btn.draw(SCREEN)

        # ===== Popup: Challenge declined (draw last) =====
        if challenge_decline_popup_open and challenge_decline_popup_by:
            overlay = pygame.Surface((MENU_WIDTH, MENU_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            SCREEN.blit(overlay, (0, 0))

            pw, ph = 560, 220
            px = (MENU_WIDTH - pw) // 2
            py = (MENU_HEIGHT - ph) // 2

            pygame.draw.rect(SCREEN, (45, 55, 75), (px, py, pw, ph), border_radius=14)
            pygame.draw.rect(SCREEN, (120, 150, 200), (px, py, pw, ph), 2, border_radius=14)

            title = font_button.render("Th\xe1ch \u0111\u1ea5u", True, WHITE)
            SCREEN.blit(title, title.get_rect(center=(px + pw // 2, py + 40)))

            msg_txt = f"{challenge_decline_popup_by} \u0111\xe3 t\u1eeb ch\u1ed1i l\u1eddi th\xe1ch \u0111\u1ea5u c\u1ee7a b\u1ea1n."
            msg_surf = font_small.render(msg_txt, True, (230, 230, 255))
            SCREEN.blit(msg_surf, msg_surf.get_rect(center=(px + pw // 2, py + 90)))

            if declined_ok_btn:
                declined_ok_btn.is_hovered(mouse_pos)
                declined_ok_btn.draw(SCREEN)

        if session_sock and time.time() - last_online_fetch > 3:
            session_sock.send(f"GET_FRIENDS_ONLINE|{current_user}")
            last_online_fetch = time.time()

        pygame.display.flip()
        clock.tick(60)



if __name__ == "__main__":
    while True:
        pre_login_menu()  
        if is_logged_in: 
            main_menu()  
        else:
            break  
        
        
               