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

def draw_input_box(surface, rect, active, text, placeholder, font, is_password=False):
    box_color = (90, 90, 90) if active else (70, 70, 70)
    border_color = (120, 180, 255) if active else (100, 100, 100)

    pygame.draw.rect(surface, box_color, rect, border_radius=14)
    pygame.draw.rect(surface, border_color, rect, width=3, border_radius=14)

    # Hiển thị placeholder nếu chưa nhập gì
    display_text = ("*" * len(text)) if is_password and text else text if text else placeholder
    color = (230, 230, 230) if text else (150, 150, 150)
    text_surface = font.render(display_text, True, color)

    # === XỬ LÝ TEXT QUÁ DÀI KHÔNG BỊ TRÀN ===
    if text_surface.get_width() > rect.width - 30:
        # Cắt phần text dư → luôn giữ phần cuối (giống input của web)
        cut_text = display_text
        while font.size(cut_text)[0] > rect.width - 30:
            cut_text = cut_text[1:]
        text_surface = font.render(cut_text, True, color)

    # Căn giữa theo chiều dọc
    text_rect = text_surface.get_rect()
    text_rect.midleft = (rect.x + 15, rect.y + rect.height // 2)
    surface.blit(text_surface, text_rect)

def login_screen():
    username = ""
    password = ""

    box_user = pygame.Rect(MENU_WIDTH//2 - 300, MENU_HEIGHT//2 - 130, 600, 85)
    box_pass = pygame.Rect(MENU_WIDTH//2 - 300, MENU_HEIGHT//2 - 25, 600, 85)

    btn_login = Button((MENU_WIDTH//2 - 230, MENU_HEIGHT//2 + 60, 460, 65), "LOGIN")
    btn_register = Button((MENU_WIDTH//2 - 230, MENU_HEIGHT//2 + 140, 460, 65), "CREATE ACCOUNT")

    active_user = False
    active_pass = False

    while True:
        SCREEN.fill((25, 25, 35))
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if box_user.collidepoint(event.pos):
                    active_user = True
                    active_pass = False
                elif box_pass.collidepoint(event.pos):
                    active_pass = True
                    active_user = False

                if btn_login.is_clicked(event):
                    return
                if btn_register.is_clicked(event):
                    return register_screen()

            if event.type == pygame.KEYDOWN:
                if active_user:
                    username = username[:-1] if event.key == pygame.K_BACKSPACE else username + event.unicode
                elif active_pass:
                    password = password[:-1] if event.key == pygame.K_BACKSPACE else password + event.unicode

        # TITLE
        title = font_title.render("WELCOME BACK", True, (220, 240, 255))
        SCREEN.blit(title, title.get_rect(center=(MENU_WIDTH//2, MENU_HEIGHT//2 - 210)))

        # INPUT BOXES
        draw_input_box(SCREEN, box_user, active_user, username, "Username", font_button)
        draw_input_box(SCREEN, box_pass, active_pass, password, "Password", font_button, is_password=True)

        # BUTTONS
        btn_login.is_hovered(mouse_pos)
        btn_register.is_hovered(mouse_pos)
        btn_login.draw(SCREEN)
        btn_register.draw(SCREEN)

        pygame.display.flip()

def register_screen():
    username = ""
    password = ""
    confirm_pass = ""

    box_user    = pygame.Rect(MENU_WIDTH//2 - 300, MENU_HEIGHT//2 - 180, 600, 85)
    box_pass    = pygame.Rect(MENU_WIDTH//2 - 300, MENU_HEIGHT//2 - 80, 600, 85)
    box_confirm = pygame.Rect(MENU_WIDTH//2 - 300, MENU_HEIGHT//2 + 20, 600, 85)


    btn_register = Button((MENU_WIDTH//2 - 230, MENU_HEIGHT//2 + 110, 460, 65), "REGISTER")
    btn_back = Button((MENU_WIDTH//2 - 230, MENU_HEIGHT//2 + 190, 460, 65), "BACK")

    active_user = active_pass = active_confirm = False
    error = ""

    while True:
        SCREEN.fill((25, 25, 35))
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if box_user.collidepoint(event.pos):
                    active_user = True; active_pass = active_confirm = False
                elif box_pass.collidepoint(event.pos):
                    active_pass = True; active_user = active_confirm = False
                elif box_confirm.collidepoint(event.pos):
                    active_confirm = True; active_user = active_pass = False

                if btn_register.is_clicked(event):
                    if password != confirm_pass:
                        error = "Passwords do not match!"
                    else:
                        return

                if btn_back.is_clicked(event):
                    return

            if event.type == pygame.KEYDOWN:
                if active_user:
                    username = username[:-1] if event.key == pygame.K_BACKSPACE else username + event.unicode
                elif active_pass:
                    password = password[:-1] if event.key == pygame.K_BACKSPACE else password + event.unicode
                elif active_confirm:
                    confirm_pass = confirm_pass[:-1] if event.key == pygame.K_BACKSPACE else confirm_pass + event.unicode

        # TITLE
        title = font_title.render("CREATE ACCOUNT", True, (220, 240, 255))
        SCREEN.blit(title, title.get_rect(center=(MENU_WIDTH//2, MENU_HEIGHT//2 - 240)))

        # INPUTS
        draw_input_box(SCREEN, box_user, active_user, username, "Choose username", font_button)
        draw_input_box(SCREEN, box_pass, active_pass, password, "Choose password", font_button, is_password=True)
        draw_input_box(SCREEN, box_confirm, active_confirm, confirm_pass, "Confirm password", font_button, is_password=True)

        # ERROR TEXT
        if error:
            err = font_button.render(error, True, (255, 120, 120))
            SCREEN.blit(err, err.get_rect(center=(MENU_WIDTH//2, MENU_HEIGHT//2 + 80)))

        # BUTTONS
        btn_register.is_hovered(mouse_pos)
        btn_back.is_hovered(mouse_pos)
        btn_register.draw(SCREEN)
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

