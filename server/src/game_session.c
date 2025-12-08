#include "../include/game_session.h"
#include "../include/utils.h"
#include "../include/elo.h"
#include "../include/database.h"

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>

#define MAX_GAMES 100
#define BOARD_N 10
#define CELLS (BOARD_N * BOARD_N)

/*
  ships1/ships2: vị trí tàu (0/1) — bí mật
  shots1/shots2: trạng thái bắn của đối thủ lên board mình (U/M/H) hoặc trạng thái bắn của mình lên enemy (tuỳ bạn muốn diễn giải)
  Ở đây ta dùng:
    - shots_by_p1: những ô P1 đã bắn lên board P2  (U/M/H)
    - shots_by_p2: những ô P2 đã bắn lên board P1  (U/M/H)
  remaining1/remaining2: số ô tàu còn lại của P1/P2
*/

typedef struct
{
    int p1, p2;
    char user1[32], user2[32];
    int elo1, elo2;

    int turn; // 1 = p1 turn, 2 = p2 turn
    int alive;

    unsigned char ships1[CELLS];
    unsigned char ships2[CELLS];

    unsigned char shots_by_p1[CELLS]; // P1 shot result on P2
    unsigned char shots_by_p2[CELLS]; // P2 shot result on P1

    int remaining1; // ship cells alive of P1
    int remaining2; // ship cells alive of P2
} Game;

static Game games[MAX_GAMES];
static int game_count = 0;

/* ===== Helpers ===== */

static int idx_of(int x, int y) { return y * BOARD_N + x; }

static void clear_board(unsigned char b[CELLS], unsigned char v) {
    for (int i = 0; i < CELLS; i++) b[i] = v;
}

/* đặt tàu ngẫu nhiên theo fleet cổ điển: 5,4,3,3,2 */
static int place_ship(unsigned char ships[CELLS], int length) {
    // thử nhiều lần để tránh kẹt
    for (int tries = 0; tries < 500; tries++) {
        int horizontal = rand() % 2;
        int x = rand() % BOARD_N;
        int y = rand() % BOARD_N;

        int dx = horizontal ? 1 : 0;
        int dy = horizontal ? 0 : 1;

        int endx = x + dx * (length - 1);
        int endy = y + dy * (length - 1);
        if (endx < 0 || endx >= BOARD_N || endy < 0 || endy >= BOARD_N) continue;

        // check overlap
        int ok = 1;
        for (int k = 0; k < length; k++) {
            int ix = x + dx * k;
            int iy = y + dy * k;
            if (ships[idx_of(ix, iy)] != 0) { ok = 0; break; }
        }
        if (!ok) continue;

        // place
        for (int k = 0; k < length; k++) {
            int ix = x + dx * k;
            int iy = y + dy * k;
            ships[idx_of(ix, iy)] = 1;
        }
        return 1;
    }
    return 0;
}

static void randomize_fleet(unsigned char ships[CELLS], int *out_remaining) {
    clear_board(ships, 0);
    int fleet[] = {5,4,3,3,2};
    int remaining = 0;
    for (int i = 0; i < 5; i++) {
        int len = fleet[i];
        if (!place_ship(ships, len)) {
            // fallback cực hiếm: clear và làm lại
            clear_board(ships, 0);
            i = -1;
            remaining = 0;
            continue;
        }
        remaining += len;
    }
    *out_remaining = remaining;
}

static Game *find_game(int sock)
{
    for (int i = 0; i < game_count; i++)
    {
        if (games[i].alive && (games[i].p1 == sock || games[i].p2 == sock))
            return &games[i];
    }
    return NULL;
}

/* ===== API ===== */

void gs_create_session(int s1, const char *u1, int e1,
                       int s2, const char *u2, int e2)
{
    if (game_count >= MAX_GAMES) {
        send_logged(s1, "ERROR|Server full\n");
        send_logged(s2, "ERROR|Server full\n");
        return;
    }

    Game *g = &games[game_count++];
    g->p1 = s1;
    g->p2 = s2;
    strncpy(g->user1, u1, sizeof(g->user1)-1);
    strncpy(g->user2, u2, sizeof(g->user2)-1);
    g->user1[sizeof(g->user1)-1] = 0;
    g->user2[sizeof(g->user2)-1] = 0;

    g->elo1 = e1;
    g->elo2 = e2;
    g->turn = 1;
    g->alive = 1;

    // init boards
    clear_board(g->shots_by_p1, 'U');
    clear_board(g->shots_by_p2, 'U');

    // auto place ships (để có HIT/MISS ngay)
    randomize_fleet(g->ships1, &g->remaining1);
    randomize_fleet(g->ships2, &g->remaining2);

    char msg1[128], msg2[128];
    snprintf(msg1, sizeof(msg1), "MATCH_FOUND|%s|%d|1\n", g->user2, g->elo2);
    snprintf(msg2, sizeof(msg2), "MATCH_FOUND|%s|%d|0\n", g->user1, g->elo1);

    send_logged(g->p1, msg1);
    send_logged(g->p2, msg2);

    printf("[GS] Creating session: %s(%d) <-> %s(%d)\n", g->user1, g->elo1, g->user2, g->elo2);
    fflush(stdout);

    send_logged(g->p1, "YOUR_TURN\n");
    send_logged(g->p2, "OPPONENT_TURN\n");
}

void gs_handle_move(int sock, int x, int y)
{
    Game *g = find_game(sock);
    if (!g) {
        send_logged(sock, "ERROR|Not in game\n");
        return;
    }

    // validate coords
    if (x < 0 || x >= BOARD_N || y < 0 || y >= BOARD_N) {
        send_logged(sock, "ERROR|Invalid coordinate\n");
        return;
    }

    int is_p1 = (sock == g->p1);
    int me_turn = is_p1 ? 1 : 2;
    int enemy_sock = is_p1 ? g->p2 : g->p1;

    // enforce turn
    if (g->turn != me_turn) {
        send_logged(sock, "ERROR|Not your turn\n");
        return;
    }

    unsigned char *my_shots = is_p1 ? g->shots_by_p1 : g->shots_by_p2;
    unsigned char *enemy_ships = is_p1 ? g->ships2 : g->ships1;
    int *enemy_remaining = is_p1 ? &g->remaining2 : &g->remaining1;

    int idx = idx_of(x, y);

    // already shot?
    if (my_shots[idx] != 'U') {
        send_logged(sock, "ERROR|Cell already targeted\n");
        return;
    }

    const char *result = "MISS";
    if (enemy_ships[idx] == 1) {
        enemy_ships[idx] = 2; // marked as hit
        my_shots[idx] = 'H';
        (*enemy_remaining)--;
        result = "HIT";
    } else {
        my_shots[idx] = 'M';
        result = "MISS";
    }

    // status
    const char *status_me = "NONE";
    const char *status_enemy = "NONE";

    if (*enemy_remaining <= 0) {
        // me wins
        status_me = "WIN";
        status_enemy = "LOSE";
        g->alive = 0;

        // (Optional) update elo here if you implement db_update_elo:
        // int newA, newB;
        // if (is_p1) elo_update_pair(g->elo1, g->elo2, 1, 32, &newA, &newB);
        // else       elo_update_pair(g->elo2, g->elo1, 1, 32, &newA, &newB);
        // db_set_elo(g->user1, new_elo1); db_set_elo(g->user2, new_elo2);
    }

    // log RX
    printf("[GS RX] sock=%d MOVE %d %d => %s (enemy_remaining=%d)\n",
           sock, x, y, result, *enemy_remaining);
    fflush(stdout);

    // send result to shooter
    char msg[128];
    snprintf(msg, sizeof(msg), "MOVE_RESULT|%d|%d|%s|STATUS=%s\n", x, y, result, status_me);
    send_logged(sock, msg);

    // notify enemy
    snprintf(msg, sizeof(msg), "OPPONENT_MOVE|%d|%d|%s|STATUS=%s\n", x, y, result, status_enemy);
    send_logged(enemy_sock, msg);

    // if game over, no more turn switching
    if (g->alive == 0) return;

    // switch turn
    g->turn = (g->turn == 1) ? 2 : 1;

    // send turn signals
    send_logged(sock, "OPPONENT_TURN\n");
    send_logged(enemy_sock, "YOUR_TURN\n");
}
