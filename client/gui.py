import pygame
import socket
import time
from network_client import NetworkClient
from dotenv import load_dotenv
import os

load_dotenv()  # đọc file .env

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


def launch_game(mode):
    print("DEBUG: launch_game() called")   # PRINT 1

    from online_battleship_gui import run_online_game
    print("DEBUG: imported online_battleship_gui")  # PRINT 2

    global SCREEN, current_user, current_password

    print("DEBUG: current_user =", current_user)    # PRINT 3
    print("DEBUG: current_pass =", current_password)    # PRINT 3

    run_online_game(current_user, current_password, mode)
    print("DEBUG: returned from run_online_game")   # PRINT 4


def send_auth_request(command, username, password):
    """
    Gửi request đăng nhập/đăng ký đến server C
    Returns: (success: bool, message: str)
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((os.getenv('IP_PUBLIC'), 5050))
        
        request = f"{command}|{username}|{password}"
        sock.send(request.encode())
        
        response = sock.recv(1024).decode()
        sock.close() 
        
        if "|" in response:
            status, message = response.split("|", 1)
            if status == "LOGIN_OK":
                return True, "Login successful!"
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
    global current_user,current_password,is_logged_in

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

                            success, msg = send_auth_request("LOGIN", username, password)
                            if success:
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
                                message = msg
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

                        success, msg = send_auth_request("LOGIN", username, password)
                        if success:
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
                            message = msg
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
    """Menu chính sau khi đăng nhập: PvP Online + Logout + Exit"""
    global current_user, is_logged_in
    
    button_width = int(MENU_WIDTH * 0.45)
    button_height = int(MENU_HEIGHT * 0.09)
    spacing = int(MENU_HEIGHT * 0.03)

    title_y_pos = int(MENU_HEIGHT * 0.15)
    start_y = title_y_pos + int(MENU_HEIGHT * 0.12)

    buttons = {
        "pvp_rank": Button(
            ((MENU_WIDTH - button_width) // 2, start_y, button_width, button_height),
            "PvP - Ranked (ELO)"
        ),
        "pvp_open": Button(
            ((MENU_WIDTH - button_width) // 2, start_y + (button_height + spacing), button_width, button_height),
            "PvP - Open Rank"
        ),
        
        "logout": Button(
            ((MENU_WIDTH - button_width) // 2, start_y + (button_height + spacing)*2, button_width, button_height),
            "Logout",
            color=LOGOUT_BUTTON_COLOR,
            hover_color=LOGOUT_BUTTON_HOVER_COLOR
        ),
        "exit": Button(
            ((MENU_WIDTH - button_width) // 2, start_y + (button_height + spacing) * 3, button_width, button_height),
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

        # User status
        status_text = f"Logged in as: {current_user}"
        status_surf = font_small.render(status_text, True, SUCCESS_COLOR)
        status_rect = status_surf.get_rect(center=(MENU_WIDTH // 2, title_y_pos + 60))
        SCREEN.blit(status_surf, status_rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                # ESC để logout và về pre-login menu
                current_user = None
                is_logged_in = False
                return

            for key, btn in buttons.items():
                if btn.is_clicked(event):
                    if key == "pvp_open":
                        launch_game('open')
                    elif key == "pvp_rank":
                        launch_game('rank')
                    elif key == "logout":
                        # Logout animation
                        SCREEN.fill(BG_COLOR)
                        logout_surf = font_title.render("Logged out successfully!", True, SUCCESS_COLOR)
                        SCREEN.blit(logout_surf, logout_surf.get_rect(center=(MENU_WIDTH//2, MENU_HEIGHT//2)))
                        pygame.display.flip()
                        pygame.time.wait(1000)
                        
                        current_user = None
                        is_logged_in = False
                        return  # Quay về pre-login menu
                    elif key == "exit":
                        pygame.quit()
                        exit()

        for btn in buttons.values():
            btn.is_hovered(mouse_pos)
            btn.draw(SCREEN)

        # Hint
        hint_surf = font_small.render("Press ESC to logout", True, (150, 150, 170))
        SCREEN.blit(hint_surf, hint_surf.get_rect(center=(MENU_WIDTH//2, MENU_HEIGHT - 50)))

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    while True:
        pre_login_menu()  
        if is_logged_in: 
            main_menu()  
        else:
            break  
        
        
               