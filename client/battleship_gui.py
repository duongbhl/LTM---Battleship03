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

# Final grid start Y
GRID_BLOCK_START_Y = GRID_BLOCK_START_Y_NO_LABELS + ACTUAL_LABEL_HEIGHT_PER_ROW

# ==== Colors ====
WHITE = (255, 255, 255)
ORANGE_HIT = (255, 165, 0)

# ==== Game Init ====
game = Game()     # engine.Game của bạn
clock = pygame.time.Clock()


# ==== MAIN LOOP ====
running = True
while running:

    # --- EVENTS ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_RETURN and game.over:
                game.reset()   # cần có trong engine


    # --- GAME LOGIC (từ engine) ---
    game.update()    # nếu engine có update()


    # --- DRAW ---
    SCREEN.fill((0, 0, 0))
    
    # 2 bản đồ (từ engine)
    grid_map = {
        "p1_ships": (GRID_BLOCK_START_X, GRID_BLOCK_START_Y),
        "p2_ships": (GRID_BLOCK_START_X + GRID_ACTUAL_SIZE + HORIZONTAL_GRID_PADDING_BETWEEN, GRID_BLOCK_START_Y)
    }

    # vẽ 2 bảng lưới
    game.draw_grids(SCREEN, SQSIZE, GRID_BLOCK_START_X, GRID_BLOCK_START_Y)

    # vẽ tàu
    if game.human1 or game.over:
        game.draw_ships(SCREEN, game.player1, *grid_map["p1_ships"])

    if game.human2 or game.over:
        game.draw_ships(SCREEN, game.player2, *grid_map["p2_ships"])

    # ==== GAME OVER TEXT ====
    if game.over:
        if game.result == 1:
            win_txt = "P1 WINS!" if game.human1 else "AI 1 WINS!"
        else:
            win_txt = "P2 WINS!" if game.human2 else "AI 2 WINS!"

        txt_s = result_font.render(win_txt, True, ORANGE_HIT)
        mid_gap_y = GRID_BLOCK_START_Y + ACTUAL_LABEL_HEIGHT_PER_ROW + GRID_ACTUAL_SIZE + VERTICAL_GRID_PADDING_BETWEEN // 2
        txt_r = txt_s.get_rect(center=(REAL_WIDTH // 2, mid_gap_y))
        SCREEN.blit(txt_s, txt_r)

        again_s = label_font.render("ENTER to Play Again", True, WHITE)
        again_r = again_s.get_rect(center=(REAL_WIDTH // 2, txt_r.bottom + int(SQSIZE * 0.7)))
        SCREEN.blit(again_s, again_r)

    # stats và legend từ engine
    game.draw_stats(SCREEN)
    game.draw_legend(SCREEN)

    pygame.display.flip()
    clock.tick(60)


pygame.quit()
