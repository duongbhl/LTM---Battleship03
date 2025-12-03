#include "../include/game_session.h"
#include "../include/utils.h"
#include "../include/elo.h"
#include "../include/database.h"

#include <stdio.h>
#include <string.h>

typedef struct {
    int p1, p2;
    char user1[32], user2[32];
    int elo1, elo2;
    int turn;
    int alive;

    char board1[100];  // 'S' = ship, 'H' = hit, 'M' = miss, 'U' = unknown
    char board2[100];
    int ships1;
    int ships2;

    int ready1;
    int ready2;
} Game;

static Game games[100];
static int game_count = 0;

// Forward Declarations
Game *find_game(int sock);
void gs_set_board(int sock, const char *csv);

Game *find_game(int sock)
{
    for (int i = 0; i < game_count; i++) {
        if (games[i].alive && (games[i].p1 == sock || games[i].p2 == sock))
            return &games[i];
    }
    return NULL;
}

void gs_set_board(int sock, const char *csv)
{
    Game *g = find_game(sock);
    if (!g) return;

    char tmp[256];
    strcpy(tmp, csv);

    char *token = strtok(tmp, ",");
    int idx = 0;

    int count_ship = 0;

    if (sock == g->p1) {
        while (token && idx < 100) {
            g->board1[idx] = token[0];
            if (token[0] == 'S') count_ship++;
            idx++;
            token = strtok(NULL, ",");
        }
        g->ships1 = count_ship;
        g->ready1 = 1;
    }
    else {
        while (token && idx < 100) {
            g->board2[idx] = token[0];
            if (token[0] == 'S') count_ship++;
            idx++;
            token = strtok(NULL, ",");
        }
        g->ships2 = count_ship;
        g->ready2 = 1;
    }

    // Khi cả 2 đã sẵn sàng → thông báo bắt đầu game
    if (g->ready1 && g->ready2) {
        send_all(g->p1, "YOUR_TURN\n", 10);
        send_all(g->p2, "OPPONENT_TURN\n", 14);
    }
}



void gs_create_session(int s1, const char *u1, int e1,
                       int s2, const char *u2, int e2)
{
    Game *g = &games[game_count++];
    g->p1 = s1;
    g->p2 = s2;
    strcpy(g->user1, u1);
    strcpy(g->user2, u2);
    g->elo1 = e1;
    g->elo2 = e2;
    g->turn = 1;
    g->alive = 1;

    char msg1[128], msg2[128];
    /* Gửi cho s1: opponent=u2, opponent_elo=e2, your_turn flag = 1 (s1 đi trước) */
    snprintf(msg1, sizeof(msg1), "MATCH_FOUND|%s|%d|1\n", u2, e2);
    /* Gửi cho s2: opponent=u1, opponent_elo=e1, your_turn flag = 0 */
    snprintf(msg2, sizeof(msg2), "MATCH_FOUND|%s|%d|0\n", u1, e1);

    printf("[GS] Creating session: %s(%d) <-> %s(%d)\n", u1, e1, u2, e2);
    printf("[GS] Send to sock %d: %s", s1, msg1);
    printf("[GS] Send to sock %d: %s", s2, msg2);
    fflush(stdout);

    send_all(s1, msg1, strlen(msg1));
    send_all(s2, msg2, strlen(msg2));

    // Yêu cầu 2 client gửi board lên server
    send_all(s1, "SEND_BOARD\n", 11);
    send_all(s2, "SEND_BOARD\n", 11);

    const char *your_turn = "YOUR_TURN\n";
    const char *opp_turn  = "OPPONENT_TURN\n";
    send_all(s1, your_turn, strlen(your_turn));
    send_all(s2, opp_turn, strlen(opp_turn));
    if (g->turn == 1) {
        printf("[TURN] %s's TURN\n", g->user1);
    } else {
        printf("[TURN] %s's TURN\n", g->user2);
    }
    fflush(stdout);

    
}




void gs_handle_move(int sock, int x, int y)
{
    Game *g = find_game(sock);
    if (!g) return;

    int me = (sock == g->p1 ? 1 : 2);
    int enemy_sock = (me == 1 ? g->p2 : g->p1);

    // log moves
    const char *me_name = (me == 1 ? g->user1 : g->user2);
    const char *enemy_name = (me == 1 ? g->user2 : g->user1);

    printf("[MOVE] %s SHOOTS at (%d,%d)\n", me_name, x, y);


    char *enemy_board = (me == 1 ? g->board2 : g->board1);
    int *enemy_ships = (me == 1 ? &g->ships2 : &g->ships1);

    int idx = y * 10 + x;

    char res[128], res2[128];

    if (enemy_board[idx] == 'S') {
        enemy_board[idx] = 'H';
        (*enemy_ships)--;
        printf("[RESULT] %s HITS\n", me_name);

        int win = (*enemy_ships == 0);

        snprintf(res, sizeof(res),
                 "MOVE_RESULT|%d|%d|HIT|STATUS=%s\n",
                 x, y, win ? "WIN" : "NONE");
        send_all(sock, res, strlen(res));

        snprintf(res2, sizeof(res2),
                 "OPPONENT_MOVE|%d|%d|HIT|STATUS=%s\n",
                 x, y, win ? "LOSE" : "NONE");
        send_all(enemy_sock, res2, strlen(res2));

        if (win) {
            g->alive = 0;
            return;
        }
    } 
    else {
        if (enemy_board[idx] != 'H') enemy_board[idx] = 'M';
        printf("[RESULT] %s MISSES\n", me_name);


        snprintf(res, sizeof(res),
                 "MOVE_RESULT|%d|%d|MISS|STATUS=NONE\n", x, y);
        send_all(sock, res, strlen(res));

        snprintf(res2, sizeof(res2),
                 "OPPONENT_MOVE|%d|%d|MISS|STATUS=NONE\n", x, y);
        send_all(enemy_sock, res2, strlen(res2));
    }

    if (me == 1) {
        printf("[TURN] %s's TURN\n", g->user2);
        send_all(g->p1, "OPPONENT_TURN\n", 14);
        send_all(g->p2, "YOUR_TURN\n", 10);
    } else {
        printf("[TURN] %s's TURN\n", g->user1);
        send_all(g->p2, "OPPONENT_TURN\n", 14);
        send_all(g->p1, "YOUR_TURN\n", 10);
    }
}
