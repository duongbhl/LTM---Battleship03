#ifndef GAME_SESSION_H
#define GAME_SESSION_H

void gs_create_session(int sock1, const char* user1, int elo1,
                       int sock2, const char* user2, int elo2,
                       int ranked);

void gs_handle_move(int sock, int x, int y);
int gs_get_opponent_sock(int sock);
void gs_send_react(int from_sock, const char *emoji);
void gs_send_chat(int from_sock, const char *msg);

/*
 * NOTE: These functions are also used by server.c.
 * The project previously relied on implicit declarations.
 */
int  gs_player_in_game(int sock);
int  gs_game_alive(int sock);
void gs_handle_disconnect(int sock);
void gs_tick_afk(void);
void gs_tick_turn_timeout(void);
void gs_forfeit(int sock);

/* Rematch (play again with the same opponent) */
void gs_request_rematch(int sock);

/* Rematch response (only the opponent of the requester should send these) */
void gs_accept_rematch(int sock);
void gs_decline_rematch(int sock);



#endif