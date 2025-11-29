import pygame
from engine import Game

pygame.init()
pygame.font.init()

SCREEN_INFO = pygame.display.Info()
REAL_WIDTH, REAL_HEIGHT = SCREEN_INFO.current_w, SCREEN_INFO.current_h
SCREEN = pygame.display.set_mode((REAL_WIDTH, REAL_HEIGHT), pygame.FULLSCREEN)

SIDE_PADDING = 25
TOP_BANNER_HEIGHT = 75
BOTTOM_BANNER_HEIGHT = int(REAL_HEIGHT * 0.22) 
if BOTTOM_BANNER_HEIGHT < 150: BOTTOM_BANNER_HEIGHT = 150 

HORIZONTAL_GRID_PADDING_BETWEEN = SIDE_PADDING * 1.5
available_width_for_grids_block = REAL_WIDTH - 2 * SIDE_PADDING
VERTICAL_GRID_PADDING_BETWEEN = SIDE_PADDING * 1.5
available_height_for_grids_block = REAL_HEIGHT - TOP_BANNER_HEIGHT - BOTTOM_BANNER_HEIGHT

pre_label_font_size = max(18, int(REAL_HEIGHT * 0.025))
ESTIMATED_LABEL_HEIGHT_PER_ROW = pre_label_font_size * 1.3

sq_from_width = (available_width_for_grids_block - HORIZONTAL_GRID_PADDING_BETWEEN) / 20.0
height_for_actual_grids_and_padding = available_height_for_grids_block - 2 * ESTIMATED_LABEL_HEIGHT_PER_ROW - VERTICAL_GRID_PADDING_BETWEEN
sq_from_height = height_for_actual_grids_and_padding / 20.0

SQSIZE = int(min(sq_from_width, sq_from_height))
if SQSIZE < 12: SQSIZE = 12

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

GRID_ACTUAL_SIZE = SQSIZE * 10
ACTUAL_LABEL_HEIGHT_PER_ROW = label_font_size * 1.3 
TOTAL_GRIDS_BLOCK_WIDTH = 2 * GRID_ACTUAL_SIZE + HORIZONTAL_GRID_PADDING_BETWEEN
GRID_BLOCK_START_X = (REAL_WIDTH - TOTAL_GRIDS_BLOCK_WIDTH) // 2
TOTAL_GRIDS_BLOCK_HEIGHT_NO_LABELS = 2 * GRID_ACTUAL_SIZE + VERTICAL_GRID_PADDING_BETWEEN 
GRID_BLOCK_START_Y_NO_LABELS = TOP_BANNER_HEIGHT + (available_height_for_grids_block - TOTAL_GRIDS_BLOCK_HEIGHT_NO_LABELS - 2 * ACTUAL_LABEL_HEIGHT_PER_ROW) // 2
GRID_BLOCK_START_Y = GRID_BLOCK_START_Y_NO_LAships
            if game.human1 or game.over: 
                draw_ships(game.player1, *grid_map["p1_ships"])
            if game.human2 or game.over: 
                draw_ships(game.player2, *grid_map["p2_ships"])
            
            # Game Over text
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
