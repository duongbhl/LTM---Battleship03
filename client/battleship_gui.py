import pygame
from engine import Game

pygame.init()
pygame.font.init()

# ==== Screen Info ====
SCREEN_INFO = pygame.display.Info()
REAL_WIDTH, REAL_HEIGHT = SCREEN_INFO.current_w, SCREEN_INFO.current_h
SCREEN = pygame.display.set_mode((REAL_WIDTH, REAL_HEIGHT), pygame.FULLSCREEN)

# ==== Layout constants ====
SIDE_PADDING = 25
TOP_BANNER_HEIGHT = 75
BOTTOM_BANNER_HEIGHT = int(REAL_HEIGHT * 0.22) 
if BOTTOM_BANNER_HEIGHT < 150: 
    BOTTOM_BANNER_HEIGHT = 150

HORIZONTAL_GRID_PADDING_BETWEEN = SIDE_PADDING * 1.5
available_width_for_grids_block = REAL_WIDTH - 2 * SIDE_PADDING
VERTICAL_GRID_PADDING_BETWEEN = SIDE_PADDING * 1.5
available_height_for_grids_block = REAL_HEIGHT - TOP_BANNER_HEIGHT - BOTTOM_BANNER_HEIGHT

# ==== Sizing ====
pre_label_font_size = max(18, int(REAL_HEIGHT * 0.025))
ESTIMATED_LABEL_HEIGHT_PER_ROW = pre_label_font_size * 1.3

sq_from_width = (available_width_for_grids_block - HORIZONTAL_GRID_PADDING_BETWEEN) / 20.0
height_for_actual_grids_and_padding = available_height_for_grids_block - 2 * ESTIMATED_LABEL_HEIGHT_PER_ROW - VERTICAL_GRID_PADDING_BETWEEN
sq_from_height = height_for_actual_grids_and_padding / 20.0

SQSIZE = int(min(sq_from_width, sq_from_height))
if SQSIZE < 12: 
    SQSIZE = 12

# ==== Fonts ====
label_font_size = max(18, int(SQSIZE * 0.45))
label_font = pygame.font.SysFont("arial", label_font_size, bold=True)
stats_font_size = max(16, int(SQSIZE * 0.4))
stats_font = pygame.font.SysFont("arial", stats_font_size)
turn_font_size = max(24, int(SQSIZE * 0.55))
turn_font = pygame.font.SysFont("arial", turn_font_size, bold=True)
result_font_size = max(40, int(SQSIZE * 0.9))
result_font = pygame.font.SysFont("arial", result_font_size, bold=True)
button_font_small_size = max(20, int(SQSIZE * 0.45))
button_font_small = pygame.font.SysFont("arial", button_font_small_size)

# ==== Grid placement ====
GRID_ACTUAL_SIZE = SQSIZE * 10
ACTUAL_LABEL_HEIGHT_PER_ROW = label_font_size * 1.3
TOTAL_GRIDS_BLOCK_WIDTH = 2 * GRID_ACTUAL_SIZE + HORIZONTAL_GRID_PADDING_BETWEEN
GRID_BLOCK_START_X = (REAL_WIDTH - TOTAL_GRIDS_BLOCK_WIDTH) // 2

TOTAL_GRIDS_BLOCK_HEIGHT_NO_LABELS = 2 * GRID_ACTUAL_SIZE + VERTICAL_GRID_PADDING_BETWEEN
GRID_BLOCK_START_Y_NO_LABELS = TOP_BANNER_HEIGHT + (available_height_for_grids_block - TOTAL_GRIDS_BLOCK_HEIGHT_NO_LABELS - 2 * ACTUAL_LABEL_HEIGHT_PER_ROW) // 2
GRID_BLOCK_START_Y = GRID_BLOCK_START_Y_NO_LABELS

GREY_BG = (40, 50, 60)
WHITE = (255, 250, 250)
GREEN_SHIP = (30, 200, 130)
BLUE_MISS = (40, 150, 220)
RED_SUNK = (255, 50, 100)
ORANGE_HIT = (255, 150, 30)
UNKNOWN_COLOR = (70, 80, 90)
HIGHLIGHT_BORDER = (255, 255, 0)
BUTTON_COLOR_GAME = (100, 100, 150)
BUTTON_HOVER_COLOR_GAME = (130, 130, 180)

COLORS = {
    "U": UNKNOWN_COLOR, 
    "M": BLUE_MISS, 
    "H": ORANGE_HIT, 
    "S": RED_SUNK
}

class InGameButton:
    def __init__(self, rect, text, font, text_color=WHITE, button_color=BUTTON_COLOR_GAME, hover_color=BUTTON_HOVER_COLOR_GAME):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.text_color = text_color
        self.button_color = button_color
        self.hover_color = hover_color
        self.hovered = False
    
    def draw(self, surface):
        color = self.hover_color if self.hovered else self.button_color
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        txt_surface = self.font.render(self.text, True, self.text_color)
        text_rect = txt_surface.get_rect(center=self.rect.center)
        surface.blit(txt_surface, text_rect)
    
    def is_hovered(self, pos):
        self.hovered = self.rect.collidepoint(pos)
        return self.hovered
    
    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hovered

def count_sunk_ships(search, target_player): 
    return sum(all(search[i] == "S" for i in ship.indexes) for ship in target_player.ships)

def draw_grid(player, left, top, search=True, is_active_player_grid=False):
    if search and is_active_player_grid:
        pygame.draw.rect(SCREEN, HIGHLIGHT_BORDER, (left - 3, top - 3, GRID_ACTUAL_SIZE + 6, GRID_ACTUAL_SIZE + 6), width=3, border_radius=5)
    
    for i in range(100):
        x = left + (i % 10) * SQSIZE
        y = top + (i // 10) * SQSIZE
        square_rect = pygame.Rect(x, y, SQSIZE, SQSIZE)
        pygame.draw.rect(SCREEN, COLORS["U"], square_rect)
        pygame.draw.rect(SCREEN, WHITE, square_rect, width=1)
        
        if search and player.search[i] != "U":
            cx = x + SQSIZE // 2
            cy = y + SQSIZE // 2
            radius_factor = 0.35 if SQSIZE > 40 else 0.4
            pygame.draw.circle(SCREEN, COLORS[player.search[i]], (cx, cy), radius=int(SQSIZE * radius_factor))

def draw_ships(player, left, top):
    INDENT = max(3, int(SQSIZE * 0.12))
    for ship in player.ships:
        x = left + ship.col * SQSIZE + INDENT
        y = top + ship.row * SQSIZE + INDENT
        width = ship.size * SQSIZE - 2 * INDENT if ship.orientation == "h" else SQSIZE - 2 * INDENT
        height = SQSIZE - 2 * INDENT if ship.orientation == "h" else ship.size * SQSIZE - 2 * INDENT
        rectangle = pygame.Rect(x, y, width, height)
        pygame.draw.rect(SCREEN, GREEN_SHIP, rectangle, border_radius=max(5, int(SQSIZE * 0.3)))

def draw_labels(grid_pos_map):
    label_bottom_offset_from_grid_top = int(ACTUAL_LABEL_HEIGHT_PER_ROW * 0.15)
    labels_data = [
        ("P1 Search", grid_pos_map["p1_search"]), 
        ("P2 Ships", grid_pos_map["p2_ships"]),
        ("P1 Ships", grid_pos_map["p1_ships"]), 
        ("P2 Search", grid_pos_map["p2_search"])
    ]
    for text, (grid_x, grid_y) in labels_data:
        txt_surf = label_font.render(text, True, WHITE)
        label_rect = txt_surf.get_rect(bottomleft=(grid_x, grid_y - label_bottom_offset_from_grid_top))
        SCREEN.blit(txt_surf, label_rect)

def draw_legend():
    items = [("Miss", BLUE_MISS), ("Hit", ORANGE_HIT), ("Sunk", RED_SUNK), ("Unknown", UNKNOWN_COLOR)]
    box_size = max(20, int(SQSIZE * 0.5))
    text_gap_from_box = 12
    line_spacing = int(label_font_size * 0.3)
    
    content_start_y_in_banner = REAL_HEIGHT - BOTTOM_BANNER_HEIGHT + SIDE_PADDING // 2
    
    max_item_width = label_font.render("Legend:", True, WHITE).get_width() 
    for label_text, _ in items:
        lw = label_font.render(label_text, True, WHITE).get_width()
        current_item_width = box_size + text_gap_from_box + lw
        if current_item_width > max_item_width: 
            max_item_width = current_item_width
    
    legend_start_x = REAL_WIDTH - SIDE_PADDING - max_item_width
    
    title_surf = label_font.render("Legend:", True, WHITE)
    title_rect = title_surf.get_rect(topleft=(legend_start_x, content_start_y_in_banner))
    SCREEN.blit(title_surf, title_rect)
    
    current_y = title_rect.bottom + line_spacing + 5
    for label_text, color in items:
        text_h = label_font.render(label_text, True, WHITE).get_height()
        box_y_offset = (text_h - box_size) // 2 if text_h > box_size else 0
        
        pygame.draw.rect(SCREEN, color, (legend_start_x, current_y + box_y_offset, box_size, box_size), border_radius=3)
        txt_surf = label_font.render(label_text, True, WHITE)
        SCREEN.blit(txt_surf, (legend_start_x + box_size + text_gap_from_box, current_y))
        current_y += max(text_h, box_size) + line_spacing 

def draw_stats(game):
    p1s = game.shots_p1
    p2s = game.shots_p2
    p1h = sum(1 for s in game.player1.search if s in("H","S"))
    p2h = sum(1 for s in game.player2.search if s in("H","S"))
    p1r = p1h/p1s*100 if p1s else 0
    p2r = p2h/p2s*100 if p2s else 0
    p1sk = count_sunk_ships(game.player1.search, game.player2)
    p2sk = count_sunk_ships(game.player2.search, game.player1)
    
    p1n = "PLAYER 1"
    p2n = "PLAYER 2"
    s1d = [f"{p1n}", f"Shots: {p1s}", f"Hits: {p1h}", f"Rate: {p1r:.1f}%", f"Sunk: {p1sk}/5"]
    s2d = [f"{p2n}", f"Shots: {p2s}", f"Hits: {p2h}", f"Rate: {p2r:.1f}%", f"Sunk: {p2sk}/5"]
    
    line_h = stats_font_size + int(stats_font_size * 0.3) 
    stats_y_start = REAL_HEIGHT - BOTTOM_BANNER_HEIGHT + SIDE_PADDING // 2
    
    p1_max_width = 0
    for i, l in enumerate(s1d):
        surf = stats_font.render(l, True, WHITE)
        if surf.get_width() > p1_max_width: 
            p1_max_width = surf.get_width()
        SCREEN.blit(surf, (SIDE_PADDING, stats_y_start + i*line_h))
    
    p2_stats_x_start = SIDE_PADDING + p1_max_width + SIDE_PADDING * 2 
    
    for i, l in enumerate(s2d):
        surf = stats_font.render(l, True, WHITE)
        SCREEN.blit(surf, (p2_stats_x_start, stats_y_start + i*line_h))

def draw_turn_indicator(game):
    if game.over: 
        return
    p_str = "P1" if game.player1_turn else "P2"
    t_str = "(H)" if (game.player1_turn and game.human1) or (not game.player1_turn and game.human2) else "(AI)"
    txt_surf = turn_font.render(f"Turn: {p_str} {t_str}", True, HIGHLIGHT_BORDER)
    txt_rect = txt_surf.get_rect(center=(REAL_WIDTH // 2, TOP_BANNER_HEIGHT // 2))
    SCREEN.blit(txt_surf, txt_rect)

def run_game_loop(human1, human2):
    game = Game(human1, human2)
    animating = True
    pausing = False
    clock = pygame.time.Clock()
    
    btn_w = int(SQSIZE * 4)
    btn_h = int(SQSIZE * 1.0)
    exit_btn_rect = pygame.Rect(REAL_WIDTH - btn_w - SIDE_PADDING, (TOP_BANNER_HEIGHT - btn_h)//2, btn_w, btn_h)
    exit_button = InGameButton(exit_btn_rect, "Exit Menu", button_font_small)
    
    grid_col1_x = GRID_BLOCK_START_X
    grid_col2_x = GRID_BLOCK_START_X + GRID_ACTUAL_SIZE + HORIZONTAL_GRID_PADDING_BETWEEN
    
    grid_row1_y = GRID_BLOCK_START_Y + ACTUAL_LABEL_HEIGHT_PER_ROW 
    grid_row2_y = grid_row1_y + GRID_ACTUAL_SIZE + VERTICAL_GRID_PADDING_BETWEEN + ACTUAL_LABEL_HEIGHT_PER_ROW 
    
    p1_search_coord = (grid_col1_x, grid_row1_y)
    p2_ships_coord = (grid_col2_x, grid_row1_y)
    p1_ships_coord = (grid_col1_x, grid_row2_y)
    p2_search_coord = (grid_col2_x, grid_row2_y)
    
    grid_map = {
        "p1_search": p1_search_coord, 
        "p2_ships": p2_ships_coord, 
        "p1_ships": p1_ships_coord, 
        "p2_search": p2_search_coord
    }
    
    p1_sr = pygame.Rect(*p1_search_coord, GRID_ACTUAL_SIZE, GRID_ACTUAL_SIZE) 
    p2_sr = pygame.Rect(*p2_search_coord, GRID_ACTUAL_SIZE, GRID_ACTUAL_SIZE) 
    
    pygame.display.set_caption(f"Battleship! (SQ: {SQSIZE})")
    
    while animating:
        m_pos = pygame.mouse.get_pos()
        m_clk = False
        
        for evt in pygame.event.get():
            if evt.type == pygame.QUIT: 
                pygame.quit()
                exit()
            
            if evt.type == pygame.KEYDOWN:
                if evt.key == pygame.K_ESCAPE: 
                    animating = False
                if evt.key == pygame.K_SPACE: 
                    pausing = not pausing
                if evt.key == pygame.K_RETURN and game.over: 
                    game = Game(human1, human2)
                    pausing = False
            
            exit_button.is_hovered(m_pos)
            if exit_button.is_clicked(evt): 
                animating = False
            
            if evt.type == pygame.MOUSEBUTTONDOWN and evt.button == 1 and not pausing and not game.over:
                m_clk = True
                if game.human1 and game.player1_turn and p1_sr.collidepoint(m_pos):
                    c = (m_pos[0] - p1_sr.left) // SQSIZE
                    r = (m_pos[1] - p1_sr.top) // SQSIZE
                    if 0 <= r < 10 and 0 <= c < 10 and game.player1.search[r*10 + c] == 'U': 
                        game.make_move(r*10 + c)
                elif game.human2 and not game.player1_turn and p2_sr.collidepoint(m_pos):
                    c = (m_pos[0] - p2_sr.left) // SQSIZE
                    r = (m_pos[1] - p2_sr.top) // SQSIZE
                    if 0 <= r < 10 and 0 <= c < 10 and game.player2.search[r*10 + c] == 'U': 
                        game.make_move(r*10 + c)
        
        if not animating: 
            break
        
        if not pausing:
            SCREEN.fill(GREY_BG)
            draw_turn_indicator(game)
            exit_button.draw(SCREEN)
            
            draw_labels(grid_map)
            
            draw_grid(game.player1, *grid_map["p1_search"], search=True, is_active_player_grid=game.player1_turn)
            draw_grid(game.player2, *grid_map["p2_ships"], search=False)
            draw_grid(game.player1, *grid_map["p1_ships"], search=False)
            draw_grid(game.player2, *grid_map["p2_search"], search=True, is_active_player_grid=not game.player1_turn)
            
            if game.human1 or game.over: 
                draw_ships(game.player1, *grid_map["p1_ships"])
            if game.human2 or game.over: 
                draw_ships(game.player2, *grid_map["p2_ships"])
            
            if game.over:
                win_txt = ("P1 WINS!" if game.human1 else "AI 1 WINS!") if game.result == 1 else ("P2 WINS!" if game.human2 else "AI 2 WINS!")
                txt_s = result_font.render(win_txt, True, ORANGE_HIT)
                mid_gap_y = GRID_BLOCK_START_Y + ACTUAL_LABEL_HEIGHT_PER_ROW + GRID_ACTUAL_SIZE + VERTICAL_GRID_PADDING_BETWEEN // 2
                txt_r = txt_s.get_rect(center=(REAL_WIDTH//2, mid_gap_y))
                SCREEN.blit(txt_s, txt_r)
                again_s = label_font.render("ENTER to Play Again", True, WHITE)
                again_r = again_s.get_rect(center=(REAL_WIDTH//2, txt_r.bottom + int(SQSIZE*0.7)))
                SCREEN.blit(again_s, again_r)
            
            draw_stats(game)
            draw_legend()
            pygame.display.flip()
        
        clock.tick(60)
        current_delay = 10
        if not pausing and not game.over:
            is_h_turn_for_delay = (game.human1 and game.player1_turn) or (game.human2 and not game.player1_turn)
            if is_h_turn_for_delay and not m_clk:
                current_delay = 30 
        elif pausing:
            current_delay = 100
        pygame.time.wait(current_delay)