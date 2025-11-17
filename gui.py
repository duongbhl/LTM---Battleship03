import pygame

pygame.init()
pygame.font.init()

AI_MAP = {"random": lambda g: g.random_ai(), "basic": lambda g: g.basic_ai(), "proba": lambda g: g.probabilistic_ai()}
AI_LABEL_MAP = {"easy": "random", "medium": "basic", "hard": "proba"}

MENU_SCREEN_INFO = pygame.display.Info()
MENU_WIDTH, MENU_HEIGHT = MENU_SCREEN_INFO.current_w, MENU_SCREEN_INFO.current_h
SCREEN = pygame.display.set_mode((MENU_WIDTH, MENU_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Battleship - Mode Selector")

BG_COLOR = (47, 79, 79); TEXT_COLOR = (240, 248, 255); BUTTON_TEXT_COLOR = (255, 255, 255)
BUTTON_COLOR = (70, 130, 180); BUTTON_HOVER_COLOR = (176, 196, 222); TITLE_COLOR = (175, 238, 238)
EXIT_BUTTON_COLOR = (200, 70, 70); EXIT_BUTTON_HOVER_COLOR = (230, 100, 100) # Colors for Exit button

title_font_size = int(MENU_HEIGHT * 0.08); button_font_size = int(MENU_HEIGHT * 0.05)
sub_screen_title_font_size = int(MENU_HEIGHT * 0.065) # For AI difficulty/selection screen titles
ai_difficulty_button_font_size = int(MENU_HEIGHT * 0.045)

font_title = pygame.font.SysFont("arial", title_font_size, bold=True)
font_button = pygame.font.SysFont("arial", button_font_size)
font_sub_screen_title = pygame.font.SysFont("arial", sub_screen_title_font_size, bold=True) # New font
font_ai_difficulty_button = pygame.font.SysFont("arial", ai_difficulty_button_font_size)


class Button:
    def __init__(self, rect, text, base_font=font_button, color=BUTTON_COLOR, hover_color=BUTTON_HOVER_COLOR): # Added color params
        self.rect = pygame.Rect(rect); self.text = text; self.hovered = False
        self.font = base_font
        self.color = color
        self.hover_color = hover_color

    def draw(self, surface):
        current_color = self.hover_color if self.hovered else self.color
        pygame.draw.rect(surface, current_color, self.rect, border_radius=10)
        txt_surface = self.font.render(self.text, True, BUTTON_TEXT_COLOR)
        text_rect = txt_surface.get_rect(center=self.rect.center)
        surface.blit(txt_surface, text_rect)
    def is_hovered(self, pos): self.hovered = self.rect.collidepoint(pos); return self.hovered
    def is_clicked(self, event): return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hovered


def launch_game(human1, human2, ai1=None, ai2=None):
    from battleship_gui import run_game_loop
    run_game_loop(human1, human2, ai1, ai2)
    global SCREEN
    SCREEN = pygame.display.set_mode((MENU_WIDTH, MENU_HEIGHT), pygame.FULLSCREEN)
    pygame.display.set_caption("Battleship - Mode Selector")

# --- New Screen for PvE AI Difficulty Selection ---
def select_pve_ai_difficulty():
    clock = pygame.time.Clock()
    screen_title_text = "Select AI Difficulty"

    btn_w = int(MENU_WIDTH * 0.33)
    btn_h = int(MENU_HEIGHT * 0.085)
    btn_spacing = int(MENU_HEIGHT * 0.03)
    
    title_area_h = int(MENU_HEIGHT * 0.25)
    start_y_buttons = title_area_h

    difficulty_options = {
        "easy": Button(((MENU_WIDTH - btn_w) // 2, start_y_buttons, btn_w, btn_h), "Easy (Random)", base_font=font_ai_difficulty_button),
        "medium": Button(((MENU_WIDTH - btn_w) // 2, start_y_buttons + btn_h + btn_spacing, btn_w, btn_h), "Medium (Basic)", base_font=font_ai_difficulty_button),
        "hard": Button(((MENU_WIDTH - btn_w) // 2, start_y_buttons + 2*(btn_h + btn_spacing), btn_w, btn_h), "Hard (Proba)", base_font=font_ai_difficulty_button),
        "back": Button(((MENU_WIDTH - btn_w) // 2, start_y_buttons + 3*(btn_h + btn_spacing) + btn_spacing*2, btn_w, btn_h), "Back to Menu", base_font=font_ai_difficulty_button, color=(100,100,100), hover_color=(130,130,130))
    }
    selected_ai_key = None

    original_caption = pygame.display.get_caption()[0]
    pygame.display.set_caption(screen_title_text)

    running_selection = True
    while running_selection:
        SCREEN.fill(BG_COLOR)
        mouse_pos = pygame.mouse.get_pos()

        title_surf = font_sub_screen_title.render(screen_title_text, True, TITLE_COLOR)
        title_rect = title_surf.get_rect(center=(MENU_WIDTH // 2, title_area_h // 2))
        SCREEN.blit(title_surf, title_rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running_selection = False # Go back
            
            for key, btn in difficulty_options.items():
                if btn.is_clicked(event):
                    if key == "back":
                        running_selection = False
                    else: # An AI difficulty was chosen
                        selected_ai_key = AI_LABEL_MAP[key]
                        running_selection = False
                    break # Stop processing clicks for this frame
            if not running_selection: break # Exit event loop if selection made or backed out

        for btn in difficulty_options.values():
            btn.is_hovered(mouse_pos)
            btn.draw(SCREEN)

        pygame.display.flip()
        clock.tick(30)
    
    pygame.display.set_caption(original_caption)
    return selected_ai_key


def main_menu():
    # Dynamic button sizing and positioning
    button_width = int(MENU_WIDTH * 0.45)
    button_height = int(MENU_HEIGHT * 0.09) # Slightly smaller main buttons
    spacing = int(MENU_HEIGHT * 0.03)
    
    title_y_pos = int(MENU_HEIGHT * 0.15)
    # Start main options a bit higher to make space for Exit button at the bottom
    start_y_main_options = title_y_pos + int(MENU_HEIGHT * 0.10)

    buttons = {
        "pve": Button(((MENU_WIDTH - button_width) // 2, start_y_main_options, button_width, button_height), "Player vs AI"),
        # "pvp_human": Button(((MENU_WIDTH - button_width) // 2, start_y_main_options + button_height + spacing, button_width, button_height), "Player vs Player"),
        "aivai": Button(((MENU_WIDTH - button_width) // 2, start_y_main_options + (button_height + spacing), button_width, button_height), "AI vs AI"),
        "exit": Button(((MENU_WIDTH - button_width) // 2, start_y_main_options + 2 * (button_height + spacing) + int(spacing*1.5), button_width, button_height), # Position Exit button lower
                       "Exit Game", color=EXIT_BUTTON_COLOR, hover_color=EXIT_BUTTON_HOVER_COLOR)
    }
    
    running = True
    while running:
        SCREEN.fill(BG_COLOR)
        mouse_pos = pygame.mouse.get_pos()

        title_surf = font_title.render("BATTLESHIP", True, TITLE_COLOR)
        title_rect = title_surf.get_rect(center=(MENU_WIDTH // 2, title_y_pos))
        SCREEN.blit(title_surf, title_rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False; pygame.quit(); exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False; pygame.quit(); exit()

            for key, btn in buttons.items(): # Only main menu buttons here
                if btn.is_clicked(event):
                    if key == "pve":
                        chosen_ai_for_pve = select_pve_ai_difficulty()
                        if chosen_ai_for_pve: # If a difficulty was selected (not backed out)
                            launch_game(True, False, None, chosen_ai_for_pve)
                    # elif key == "pvp_human":
                    #     launch_game(True, True) 
                    elif key == "aivai":
                        selected_ai1 = select_ai("Select AI for Computer 1") # Changed title
                        if selected_ai1:
                            selected_ai2 = select_ai("Select AI for Computer 2") # Changed title
                            if selected_ai2:
                                launch_game(False, False, selected_ai1, selected_ai2)
                    elif key == "exit":
                        running = False
                        pygame.quit()
                        exit()

        for btn in buttons.values():
            btn.is_hovered(mouse_pos)
            btn.draw(SCREEN)
        
        pygame.display.flip()

# select_ai function for AI vs AI (largely unchanged, but can use new fonts/sizing)
def select_ai(title_text):
    clock = pygame.time.Clock()
    btn_w = int(MENU_WIDTH * 0.35); btn_h = int(MENU_HEIGHT * 0.09)
    btn_spacing = int(MENU_HEIGHT * 0.03)
    title_area_h = int(MENU_HEIGHT * 0.25)
    start_y_buttons = title_area_h

    ai_buttons_selection = {
        "random": Button(((MENU_WIDTH - btn_w)//2, start_y_buttons, btn_w, btn_h), "Random AI", base_font=font_ai_difficulty_button),
        "basic": Button(((MENU_WIDTH - btn_w)//2, start_y_buttons + btn_h + btn_spacing, btn_w, btn_h), "Basic AI", base_font=font_ai_difficulty_button),
        "proba": Button(((MENU_WIDTH - btn_w)//2, start_y_buttons + 2*(btn_h + btn_spacing), btn_w, btn_h), "Proba AI", base_font=font_ai_difficulty_button),
        "back": Button(((MENU_WIDTH - btn_w) // 2, start_y_buttons + 3*(btn_h + btn_spacing) + btn_spacing*2, btn_w, btn_h), "Back to Menu", base_font=font_ai_difficulty_button, color=(100,100,100), hover_color=(130,130,130))
    }
    selected_option = None
    original_caption = pygame.display.get_caption()[0]
    pygame.display.set_caption(title_text)

    running_selection = True
    while running_selection:
        SCREEN.fill(BG_COLOR)
        mouse_pos = pygame.mouse.get_pos()
        title_surf = font_sub_screen_title.render(title_text, True, TITLE_COLOR)
        title_rect = title_surf.get_rect(center=(MENU_WIDTH // 2, title_area_h // 2))
        SCREEN.blit(title_surf, title_rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running_selection = False
            for key, btn in ai_buttons_selection.items():
                if btn.is_clicked(event):
                    if key == "back":
                        running_selection = False
                    else:
                        selected_option = key; running_selection = False
                    break
            if not running_selection: break
        
        for btn in ai_buttons_selection.values():
            btn.is_hovered(mouse_pos)
            btn.draw(SCREEN)
        pygame.display.flip()
        clock.tick(30)
    
    pygame.display.set_caption(original_caption)
    return selected_option

if __name__ == "__main__":
    main_menu()