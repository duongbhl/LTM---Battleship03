#ifndef GAME_SESSION_H
#define GAME_SESSION_H

void gs_create_session(int sock1, const char* user1, int elo1,
                       int sock2, const char* user2, int elo2);
void gs_tick_afk(void);
void gs_forfeit(int sock);
void gs_set_board(int sock, const char *csv);
void gs_handle_move(int sock, int x, int y);
void gs_handle_disconnect(int sock);
void gs_tick_afk(void);
int gs_get_other_player(int sock);

#endif
