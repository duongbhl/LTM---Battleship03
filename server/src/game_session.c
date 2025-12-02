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
    int turn;   // 1 hoặc 2
    int alive;
} Game;

static Game games[100];
static int game_count = 0;

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

    const char *your_turn = "YOUR_TURN\n";
    const char *opp_turn  = "OPPONENT_TURN\n";
    send_all(s1, your_turn, strlen(your_turn));
    send_all(s2, opp_turn, strlen(opp_turn));
}


Game *find_game(int sock)
{
    for (int i = 0; i < game_count; i++) {
        if (games[i].alive && (games[i].p1 == sock || games[i].p2 == sock))
            return &games[i];
    }
    return NULL;
}

void gs_handle_move(int sock, int x, int y)
{
    Game *g = find_game(sock);
    if (!g) return;

    int me = (sock == g->p1) ? 1 : 2;
    int enemy = (me == 1 ? g->p2 : g->p1);

    // GIẢ LẬP: mọi phát bắn đều MISS để demo
    char msg[64];
    snprintf(msg, sizeof(msg), "MOVE_RESULT|%d|%d|MISS|STATUS=NONE\n", x, y);
    send_all(sock, msg, strlen(msg));

    snprintf(msg, sizeof(msg), "OPPONENT_MOVE|%d|%d|MISS|STATUS=NONE\n", x, y);
    send_all(enemy, msg, strlen(msg));

    // chuyển lượt
    if (me == 1) {
        send_all(g->p1, "OPPONENT_TURN\n", 14);
        send_all(g->p2, "YOUR_TURN\n", 10);
    } else {
        send_all(g->p2, "OPPONENT_TURN\n", 14);
        send_all(g->p1, "YOUR_TURN\n", 10);
    }
}
