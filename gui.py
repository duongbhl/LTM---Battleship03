import pygame
import socket


pygame.init()
pygame.font.init()

MENU_SCREEN_INFO = pygame.display.Info()
MENU_WIDTH, MENU_HEIGHT = MENU_SCREEN_INFO.current_w, MENU_SCREEN_INFO.current_h
SCREEN = pygame.display.set_mode((MENU_WIDTH, MENU_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Battleship - Mode Selector")

BG_COLOR = (47, 79, 79)
TEXT_COLOR = (240, 248, 255)
BUTTON_TEXT_COLOR = (255, 255, 255)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER_COLOR = (176, 196, 222)
TITLE_COLOR = (175, 238, 238)
EXIT_BUTTON_COLOR = (200, 70, 70)
EXIT_BUTTON_HOVER_COLOR = (230, 100, 100)

title_font_size = int(MENU_HEIGHT * 0.08)
button_font_size = int(MENU_HEIGHT * 0.05)

font_title = pygame.font.SysFont("arial", title_font_size, bold=True)
font_button = pygame.font.SysFont("arial", button_font_size)


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


def launch_game():
    from battleship_gui import run_game_loop
    # Chỉ human vs human (PvP)
    run_game_loop(True, True)
    global SCREEN
    SCREEN = pygame.display.set_mode((MENU_WIDTH, MENU_HEIGHT), pygame.FULLSCREEN)
    pygame.display.set_caption("Battleship - Mode Selector")

def login_screen():
    input_box_user = pygame.Rect(MENU_WIDTH//2 - 200, MENU_HEIGHT//2 - 120, 400, 60)
    input_box_pass = pygame.Rect(MENU_WIDTH//2 - 200, MENU_HEIGHT//2, 400, 60)
    btn_login = Button((MENU_WIDTH//2 - 200, MENU_HEIGHT//2 + 120, 400, 70), "Login")
    btn_register = Button((MENU_WIDTH//2 - 200, MENU_HEIGHT//2 + 210, 400, 70), "Create a new account")

    username = ""
    password = ""
    active_user = False
    active_pass = False

    while True:
        SCREEN.fill((30, 30, 30))
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box_user.collidepoint(event.pos):
                    active_user = True
                    active_pass = False
                elif input_box_pass.collidepoint(event.pos):
                    active_pass = True
                    active_user = False

                if btn_login.is_clicked(event):
                    # Gửi gói tin LOGIN đến server TCP
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect(("127.0.0.1", 5000))
                    sock.send(f"LOGIN|{username}|{password}".encode())
                    resp = sock.recv(1024).decode()

                    if resp == "LOGIN_OK":
                        return  # chuyển sang main_menu()
                    else:
                        print("Login failed:", resp)

                if btn_register.is_clicked(event):
                    return register_screen()

            if event.type == pygame.KEYDOWN:
                if active_user:
                    if event.key == pygame.K_BACKSPACE:
                        username = username[:-1]
                    else:
                        username += event.unicode
                elif active_pass:
                    if event.key == pygame.K_BACKSPACE:
                        password = password[:-1]
                    else:
                        password += event.unicode

        # Draw UI
        title_surf = font_title.render("LOGIN", True, TITLE_COLOR)
        title_rect = title_surf.get_rect(center=(MENU_WIDTH//2, MENU_HEIGHT//2 - 220))
        SCREEN.blit(title_surf, title_rect)

        # Input boxes
        color_user = (120, 120, 120) if active_user else (80, 80, 80)
        color_pass = (120, 120, 120) if active_pass else (80, 80, 80)
        
        pygame.draw.rect(SCREEN, color_user, input_box_user, 0, 8)
        pygame.draw.rect(SCREEN, color_pass, input_box_pass, 0, 8)

        user_text = font_button.render(username or "Username", True, (255, 255, 255) if username else (150, 150, 150))
        pass_text = font_button.render("*" * len(password) if password else "Password", True, (255, 255, 255) if password else (150, 150, 150))

        SCREEN.blit(user_text, (input_box_user.x + 10, input_box_user.y + 10))
        SCREEN.blit(pass_text, (input_box_pass.x + 10, input_box_pass.y + 10))
        btn_login.is_hovered(mouse_pos)
        btn_register.is_hovered(mouse_pos)

        btn_login.draw(SCREEN)
        btn_register.draw(SCREEN)

        pygame.display.flip()

def register_screen():
    input_user = ""
    input_pass = ""

    box_user = pygame.Rect(MENU_WIDTH//2 - 200, MENU_HEIGHT//2 - 120, 400, 60)
    box_pass = pygame.Rect(MENU_WIDTH//2 - 200, MENU_HEIGHT//2, 400, 60)
    btn_ok = Button((MENU_WIDTH//2 - 200, MENU_HEIGHT//2 + 120, 400, 70), "Register")
    btn_back = Button((MENU_WIDTH//2 - 200, MENU_HEIGHT//2 + 210, 400, 70), "Back to main menu")

    active_user = False
    active_pass = False

    while True:
        SCREEN.fill((40, 40, 40))
        mouse = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if box_user.collidepoint(event.pos):
                    active_user = True
                    active_pass = False
                elif box_pass.collidepoint(event.pos):
                    active_pass = True
                    active_user = False

                if btn_ok.is_clicked(event):
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect(("127.0.0.1", 5000))
                    sock.send(f"REGISTER|{input_user}|{input_pass}".encode())
                    resp = sock.recv(1024).decode()

                    print("REGISTER:", resp)
                    return  

                if btn_back.is_clicked(event):
                    return  

            if event.type == pygame.KEYDOWN:
                if active_user:
                    if event.key == pygame.K_BACKSPACE:
                        input_user = input_user[:-1]
                    else:
                        input_user += event.unicode
                elif active_pass:
                    if event.key == pygame.K_BACKSPACE:
                        input_pass = input_pass[:-1]
                    else:
                        input_pass += event.unicode
        #Draw UI
        title_surf = font_title.render("REGISTER", True, TITLE_COLOR)
        title_rect = title_surf.get_rect(center=(MENU_WIDTH//2, MENU_HEIGHT//2 - 220))
        SCREEN.blit(title_surf, title_rect)

        # Input boxes
        color_user = (120, 120, 120) if active_user else (80, 80, 80)
        color_pass = (120, 120, 120) if active_pass else (80, 80, 80)

        pygame.draw.rect(SCREEN, color_user, box_user, 0, 8)
        pygame.draw.rect(SCREEN, color_pass, box_pass, 0, 8)

        user_surf = font_button.render(input_user or "Username", True, (255, 255, 255) if input_user else (150, 150, 150))
        pass_surf = font_button.render("*"*len(input_pass) if input_pass else "Password", True, (255, 255, 255) if input_pass else (150, 150, 150))

        SCREEN.blit(user_surf, (box_user.x+10, box_user.y+10))
        SCREEN.blit(pass_surf, (box_pass.x+10, box_pass.y+10))

        btn_ok.is_hovered(mouse)
        btn_back.is_hovered(mouse)

        btn_ok.draw(SCREEN)
        btn_back.draw(SCREEN)

        pygame.display.flip()


def main_menu():
    button_width = int(MENU_WIDTH * 0.45)
    button_height = int(MENU_HEIGHT * 0.09)
    spacing = int(MENU_HEIGHT * 0.03)

    title_y_pos = int(MENU_HEIGHT * 0.15)
    start_y_main_options = title_y_pos + int(MENU_HEIGHT * 0.1)

    buttons = {
        "login": Button(
            ((MENU_WIDTH - button_width) // 2, start_y_main_options, button_width, button_height),
            "Login/Register"
        ),
        "pvp": Button(
            ((MENU_WIDTH - button_width) // 2, start_y_main_options + (button_height + spacing), button_width, button_height),
            "PvP Online"
        ),
        "exit": Button(
            ((MENU_WIDTH - button_width) // 2, start_y_main_options + (button_height + spacing) * 2, button_width, button_height),
            "Exit Game",
            color=EXIT_BUTTON_COLOR,
            hover_color=EXIT_BUTTON_HOVER_COLOR
        )
    }

    running = True
    while running:
        SCREEN.fill(BG_COLOR)
        mouse_pos = pygame.mouse.get_pos()

        title_surf = font_title.render("BATTLESHIP", True, TITLE_COLOR)
        title_rect = title_surf.get_rect(center=(MENU_WIDTH // 2, title_y_pos))
        SCREEN.blit(title_surf, title_rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
                exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
                pygame.quit()
                exit()

            for key, btn in buttons.items():
                if btn.is_clicked(event):
                    if key == "login":
                        login_screen()
                    elif key == "register":
                        register_screen()
                    elif key == "pvp":
                        launch_game()
                    elif key == "exit":
                        running = False
                        pygame.quit()
                        exit()


        for btn in buttons.values():
            btn.is_hovered(mouse_pos)
            btn.draw(SCREEN)

        pygame.display.flip()


if __name__ == "__main__":
    main_menu()

