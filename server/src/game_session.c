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

typedef struct
{
    int p1, p2;
    char user1[32], user2[32];
    int elo1, elo2;

    int turn; 
    int alive;

    int dc_sock;            
    time_t dc_expire; 

    unsigned char ships1[CELLS];
    unsigned char ships2[CELLS];

    unsigned char shots_by_p1[CELLS];
    unsigned char shots_by_p2[CELLS];

    int remaining1;
    int remaining2;
} Game;

static Game games[MAX_GAMES];
static int game_count = 0;

/* Helpers */
static int idx_of(int x, int y) { return y * BOARD_N + x; }

static void clear_board(unsigned char b[CELLS], unsigned char v)
{
    for (int i = 0; i < CELLS; i++)
        b[i] = v;
}

static int place_ship(unsigned char ships[CELLS], int length)
{
    for (int tries = 0; tries < 500; tries++)
    {
        int horizontal = rand() % 2;
        int x = rand() % BOARD_N;
        int y = rand() % BOARD_N;

        int dx = horizontal ? 1 : 0;
        int dy = horizontal ? 0 : 1;

        int endx = x + dx * (length - 1);
        int endy = y + dy * (length - 1);
        if (endx < 0 || endx >= BOARD_N || endy < 0 || endy >= BOARD_N)
            continue;

        int ok = 1;

        // 1) các ô tàu không được trùng tàu khác
        for (int k = 0; k < length; k++)
        {
            int ix = x + dx * k;
            int iy = y + dy * k;
            if (ships[idx_of(ix, iy)] != 0)
            {
                ok = 0;
                break;
            }
        }
        if (!ok) continue;

        // 2) check xung quanh tàu
        int minx = x - 1;
        int maxx = endx + 1;
        int miny = y - 1;
        int maxy = endy + 1;

        if (minx < 0) minx = 0;
        if (miny < 0) miny = 0;
        if (maxx >= BOARD_N) maxx = BOARD_N - 1;
        if (maxy >= BOARD_N) maxy = BOARD_N - 1;

        for (int iy = miny; iy <= maxy; iy++)
        {
            for (int ix = minx; ix <= maxx; ix++)
            {
                // nếu ô thuộc thân tàu → bỏ qua
                int inside = 0;

                for (int k = 0; k < length; k++)
                {
                    int tx = x + dx * k;
                    int ty = y + dy * k;
                    if (tx == ix && ty == iy)
                    {
                        inside = 1;
                        break;
                    }
                }

                if (!inside && ships[idx_of(ix, iy)] != 0)
                {
                    ok = 0;
                    goto SKIP_PLACEMENT;
                }
            }
        }

SKIP_PLACEMENT:
        if (!ok) continue;

        for (int k = 0; k < length; k++)
        {
            int ix = x + dx * k;
            int iy = y + dy * k;
            ships[idx_of(ix, iy)] = 1;
        }
        return 1;
    }
    return 0;
}

static void randomize_fleet(unsigned char ships[CELLS], int *out_remaining)
{
    clear_board(ships, 0);
    int fleet[] = {5, 4, 3, 3, 2};
    int remaining = 0;
    for (int i = 0; i < 5; i++)
    {
        int len = fleet[i];
        if (!place_ship(ships, len))
        {
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
        if (games[i].alive &&
            (games[i].p1 == sock || games[i].p2 == sock))
            return &games[i];
    }
    return NULL;
}

int gs_player_in_game(int sock)
{
    return (find_game(sock) != NULL);
}

int gs_game_alive(int sock)
{
    Game *g = find_game(sock);
    return (g && g->alive);
}

/* ===== API ===== */

// Find all contiguous ship cells belonging to the same ship
static int collect_ship_cells(unsigned char ships[], int idx, int out_cells[], int *out_count)
{
    int cx = idx % BOARD_N;
    int cy = idx / BOARD_N;

    int count = 0;

    // 1) Kiểm tra tàu nằm ngang
    int left = cx, right = cx;
    while (left > 0     && ships[cy * BOARD_N + (left - 1)] != 0) left--;
    while (right < 9    && ships[cy * BOARD_N + (right + 1)] != 0) right++;

    if (left != right)  // tàu nằm ngang
    {
        for (int x = left; x <= right; x++)
        {
            int id = cy * BOARD_N + x;
            out_cells[count++] = id;
        }
        *out_count = count;
        return 1;
    }

    // 2) Không phải tàu ngang → thử tàu dọc
    int top = cy, bottom = cy;
    while (top > 0      && ships[(top - 1) * BOARD_N + cx] != 0) top--;
    while (bottom < 9   && ships[(bottom + 1) * BOARD_N + cx] != 0) bottom++;

    for (int y = top; y <= bottom; y++)
    {
        int id = y * BOARD_N + cx;
        out_cells[count++] = id;
    }

    *out_count = count;
    return 1;
}


// Check if all those cells are hit = 2
static int ship_is_sunk(unsigned char ships[], int cells[], int count)
{
    for (int i = 0; i < count; i++)
    {
        if (ships[cells[i]] != 2) return 0;
    }
    return 1;
}


void gs_create_session(int s1, const char *u1, int e1,
                       int s2, const char *u2, int e2)
{
    if (game_count >= MAX_GAMES)
    {
        send_logged(s1, "ERROR|Server full\n");
        send_logged(s2, "ERROR|Server full\n");
        return;
    }

    Game *g = &games[game_count++];
    g->p1 = s1;
    g->p2 = s2;
    strncpy(g->user1, u1, 31);
    strncpy(g->user2, u2, 31);
    g->user1[31] = 0;
    g->user2[31] = 0;

    g->elo1 = e1;
    g->elo2 = e2;

    g->turn = 1;
    g->alive = 1;

    g->dc_sock = 0;
    g->dc_expire = 0;


    clear_board(g->shots_by_p1, 'U');
    clear_board(g->shots_by_p2, 'U');

    randomize_fleet(g->ships1, &g->remaining1);
    randomize_fleet(g->ships2, &g->remaining2);

    /* Send MATCH_FOUND */
    char msg1[128], msg2[128];
    snprintf(msg1, sizeof(msg1), "MATCH_FOUND|%s|%d|1\n",
             g->user2, g->elo2);
    snprintf(msg2, sizeof(msg2), "MATCH_FOUND|%s|%d|0\n",
             g->user1, g->elo1);

    send_logged(g->p1, msg1);
    send_logged(g->p2, msg2);

    //Send ships to each player */
    char buf1[200], buf2[200], send1[240], send2[240];

    for (int i = 0; i < CELLS; i++)
    {
        buf1[i] = g->ships1[i] ? '1' : '0';
        buf2[i] = g->ships2[i] ? '1' : '0';
    }
    buf1[CELLS] = 0;
    buf2[CELLS] = 0;

    snprintf(send1, sizeof(send1), "MY_SHIPS|%s\n", buf1);
    snprintf(send2, sizeof(send2), "MY_SHIPS|%s\n", buf2);

    send_logged(g->p1, send1);
    send_logged(g->p2, send2);

    send_logged(g->p1, "YOUR_TURN\n");
    send_logged(g->p2, "OPPONENT_TURN\n");
}

void gs_handle_move(int sock, int x, int y)
{
    Game *g = find_game(sock);
    if (!g)
    {
        send_logged(sock, "ERROR|Not in game\n");
        return;
    }

    if (x < 0 || x >= BOARD_N || y < 0 || y >= BOARD_N)
    {
        send_logged(sock, "ERROR|Invalid coordinate\n");
        return;
    }

    int is_p1 = (sock == g->p1);
    int me_turn = is_p1 ? 1 : 2;
    int enemy_sock = is_p1 ? g->p2 : g->p1;

    if (g->turn != me_turn)
    {
        send_logged(sock, "ERROR|Not your turn\n");
        return;
    }

    unsigned char *my_shots = is_p1 ? g->shots_by_p1 : g->shots_by_p2;
    unsigned char *enemy_ships = is_p1 ? g->ships2 : g->ships1;
    int *enemy_remaining = is_p1 ? &g->remaining2 : &g->remaining1;

    int idx = idx_of(x, y);

    if (my_shots[idx] != 'U')
    {
        send_logged(sock, "ERROR|Cell already targeted\n");
        return;
    }

    int is_hit = (enemy_ships[idx] == 1);
    const char *result;

    int cells[16];
    int count = 0;

    if (is_hit)
    {
        enemy_ships[idx] = 2;
        my_shots[idx] = 'H';
        (*enemy_remaining)--;

        // detect ship's full segment 
        collect_ship_cells(enemy_ships, idx, cells, &count);
        int sunk = ship_is_sunk(enemy_ships, cells, count);
        result = sunk ? "SUNK" : "HIT";
    }

    else
    {
        my_shots[idx] = 'M';
        result = "MISS";
    }

    const char *status_me = "NONE";
    const char *status_enemy = "NONE";

    if (*enemy_remaining <= 0)
    {
        status_me = "WIN";
        status_enemy = "LOSE";
        g->alive = 0;
    }
    
    char msg[256];

    if (strcmp(result, "SUNK") == 0)
    {
        char list[128] = "";
        for (int i = 0; i < count; i++)
        {
            char t[16];
            sprintf(t, "%d,", cells[i]);
            strcat(list, t);
        }
        if (count > 0) list[strlen(list)-1] = 0; // remove last comma

        snprintf(msg, sizeof(msg),
                "MOVE_RESULT|%d|%d|HIT|STATUS=SUNK|%s\n",
                x, y, list);
    }

    else
    {
        snprintf(msg, sizeof(msg),
                "MOVE_RESULT|%d|%d|%s|STATUS=%s\n",
                x, y, result, status_me);
    }
    send_logged(sock, msg);


    if (strcmp(result, "SUNK") == 0)
    {
        char list[128] = "";
        for (int i = 0; i < count; i++)
        {
            char t[16];
            sprintf(t, "%d,", cells[i]);
            strcat(list, t);
        }
        if (count > 0) list[strlen(list) - 1] = 0; // remove trailing comma

        snprintf(msg, sizeof(msg),
                "OPPONENT_MOVE|%d|%d|HIT|STATUS=SUNK|%s\n",
                x, y, list);
    }

    else
    {
        snprintf(msg, sizeof(msg),
                "OPPONENT_MOVE|%d|%d|%s|STATUS=%s\n",
                x, y, result, status_enemy);
    }
    send_logged(enemy_sock, msg);


    if (!g->alive)
        send_logged(sock,       "GAMEOVER|WIN\n");
        send_logged(enemy_sock, "GAMEOVER|LOSE\n");
        return;

    if (!is_hit)
    {
        g->turn = (g->turn == 1 ? 2 : 1);
        send_logged(sock, "OPPONENT_TURN\n");
        send_logged(enemy_sock, "YOUR_TURN\n");
    }
    else
    {
        send_logged(sock, "YOUR_TURN\n");
        send_logged(enemy_sock, "OPPONENT_TURN\n");
    }
}

void gs_handle_disconnect(int sock)
{
    Game *g = find_game(sock);
    if (!g || g->alive == 0)
        return;

    g->dc_sock = sock;
    g->dc_expire = time(NULL) + 30;

    int other = (sock == g->p1 ? g->p2 : g->p1);

    char msg[64];
    snprintf(msg, sizeof(msg), "OPPONENT_DISCONNECTED|30\n");
    send_logged(other, msg);
}

void gs_tick_afk(void)
{
    time_t now = time(NULL);

    for (int i = 0; i < game_count; i++)
    {
        Game *g = &games[i];
        if (!g->alive) continue;

        if (g->dc_sock != 0 && now >= g->dc_expire)
        {
            gs_forfeit(g->dc_sock);
            g->dc_sock = 0;
        }
    }
}

void gs_forfeit(int sock)
{
    Game *g = find_game(sock);
    if (!g || !g->alive)
        return;

    int is_p1 = (sock == g->p1);
    int winner_sock = is_p1 ? g->p2 : g->p1;

    send_logged(winner_sock, "GAMEOVER|WIN\n");
    send_logged(sock,         "GAMEOVER|LOSE\n");

    g->alive = 0;
    g->dc_sock = 0;
    g->dc_expire = 0;
}
