#ifndef GAME_SESSION_H
#define GAME_SESSION_H

#define MAX_GAMES 100
#define BOARD_N 10
#define CELLS (BOARD_N * BOARD_N)
#define MAX_SPECTATORS 8
#include <time.h>

typedef struct
{
    int p1, p2;
    char user1[32], user2[32];
    int ranked;
    int elo1, elo2;

    int turn;
    int alive;
    time_t turn_started_at;   // thời điểm bắt đầu lượt hiện tại

    int dc_sock;
    time_t dc_expire;

    unsigned char ships1[CELLS];
    unsigned char ships2[CELLS];

    unsigned char shots_by_p1[CELLS];
    unsigned char shots_by_p2[CELLS];

    int remaining1;
    int remaining2;

    int spectators[MAX_SPECTATORS];
    int spectator_count;


    /* Rematch handshake (after GAMEOVER) */
    int rematch1;
    int rematch2;

    int left1;
    int left2;


} Game;

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

void gs_handle_disconnect(int sock);

void gs_handle_leave(int sock);

void gs_finish_game(Game *g, int winner_sock, const char *reason);

int gs_add_spectator(Game *gs, int sock);

void gs_remove_spectator(Game *gs, int sock);

Game *gs_find_by_player(int sock);

#endif