#include "../include/game_session.h"
#include "../include/utils.h"
#include "../include/elo.h"
#include "../include/database.h"
#include "../include/server.h"
#include "../include/online_users.h"

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>

static Game games[MAX_GAMES];
static int game_count = 0;

/* Helpers */
static Game *alloc_game_slot(void)
{
    // reuse slot đã kết thúc
    for (int i = 0; i < game_count; i++)
    {
        if (!games[i].alive && games[i].p1 == 0 && games[i].p2 == 0)
            return &games[i];
    }

    // mở slot mới nếu còn chỗ
    if (game_count < MAX_GAMES)
        return &games[game_count++];

    return NULL;
}

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
        if (!ok)
            continue;

        // 2) check xung quanh tàu
        int minx = x - 1;
        int maxx = endx + 1;
        int miny = y - 1;
        int maxy = endy + 1;

        if (minx < 0)
            minx = 0;
        if (miny < 0)
            miny = 0;
        if (maxx >= BOARD_N)
            maxx = BOARD_N - 1;
        if (maxy >= BOARD_N)
            maxy = BOARD_N - 1;

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
        if (!ok)
            continue;

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

/* Find the most recent game for this socket (alive or finished). */
static Game *find_game_any(int sock)
{
    for (int i = game_count - 1; i >= 0; i--)
    {
        if (games[i].p1 == sock || games[i].p2 == sock)
            return &games[i];
    }
    return NULL;
}

int gs_get_opponent_sock(int sock)
{
    Game *g = find_game(sock);
    if (!g || !g->alive)
        return -1;

    return (sock == g->p1) ? g->p2 : g->p1;
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

// Find all contiguous ship cells belonging to the same ship
static int collect_ship_cells(unsigned char ships[], int idx, int out_cells[], int *out_count)
{
    int cx = idx % BOARD_N;
    int cy = idx / BOARD_N;

    int count = 0;

    // 1) Kiểm tra tàu nằm ngang
    int left = cx, right = cx;
    while (left > 0 && ships[cy * BOARD_N + (left - 1)] != 0)
        left--;
    while (right < 9 && ships[cy * BOARD_N + (right + 1)] != 0)
        right++;

    if (left != right) // tàu nằm ngang
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
    while (top > 0 && ships[(top - 1) * BOARD_N + cx] != 0)
        top--;
    while (bottom < 9 && ships[(bottom + 1) * BOARD_N + cx] != 0)
        bottom++;

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
        if (ships[cells[i]] != 2)
            return 0;
    }
    return 1;
}

// Create a new game session
void gs_create_session(int s1, const char *u1, int e1, int s2, const char *u2, int e2, int ranked)
{
    Game *g = alloc_game_slot();
    if (!g)
    {
        send_logged(s1, "ERROR|Server full\n");
        send_logged(s2, "ERROR|Server full\n");
        return;
    }

    /* reset sạch struct để tránh dính game cũ */
    memset(g, 0, sizeof(*g));

    g->p1 = s1;
    g->p2 = s2;

    strncpy(g->user1, u1, 31);
    strncpy(g->user2, u2, 31);
    g->user1[31] = 0;
    g->user2[31] = 0;

    g->elo1 = e1;
    g->elo2 = e2;
    g->ranked = ranked;

    g->turn = 1;
    g->alive = 1;
    g->turn_started_at = time(NULL);

    g->rematch1 = 0;
    g->rematch2 = 0;

    g->dc_sock = 0;
    g->dc_expire = 0;
    g->spectator_count = 0;

    clear_board(g->shots_by_p1, 'U');
    clear_board(g->shots_by_p2, 'U');

    randomize_fleet(g->ships1, &g->remaining1);
    randomize_fleet(g->ships2, &g->remaining2);

    /* ===== MATCH_FOUND ===== */
    char msg1[128], msg2[128];
    snprintf(msg1, sizeof(msg1), "MATCH_FOUND|%s|%d|1\n",
             g->user2, g->elo2);
    snprintf(msg2, sizeof(msg2), "MATCH_FOUND|%s|%d|0\n",
             g->user1, g->elo1);

    send_logged(g->p1, msg1);
    send_logged(g->p2, msg2);

    /* ===== SEND SHIPS ===== */
    char buf1[CELLS + 1], buf2[CELLS + 1];
    char send1[240], send2[240];

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

// Handle a player's move
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
    const char *shooter_side = is_p1 ? "P1" : "P2";
    const char *target_side = is_p1 ? "P2" : "P1";
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

        collect_ship_cells(enemy_ships, idx, cells, &count);
        result = ship_is_sunk(enemy_ships, cells, count) ? "SUNK" : "HIT";
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
        /* game will be finished after sending move results */
    }

    char msg[256];

    /* ===== PLAYER ===== */
    if (strcmp(result, "SUNK") == 0)
    {
        char list[128] = "";
        for (int i = 0; i < count; i++)
        {
            char t[16];
            sprintf(t, "%d,", cells[i]);
            strcat(list, t);
        }
        if (count > 0)
            list[strlen(list) - 1] = 0;

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

    /* ===== ENEMY ===== */
    if (strcmp(result, "SUNK") == 0)
    {
        char list[128] = "";
        for (int i = 0; i < count; i++)
        {
            char t[16];
            sprintf(t, "%d,", cells[i]);
            strcat(list, t);
        }
        if (count > 0)
            list[strlen(list) - 1] = 0;

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

    /* ===== SPECTATORS =====
        gửi TARGET_SIDE để spectator update đúng board bị bắn */
    if (strcmp(result, "SUNK") == 0)
    {
        char list[128] = "";
        for (int i = 0; i < count; i++)
        {
            char t[16];
            sprintf(t, "%d,", cells[i]);
            strcat(list, t);
        }
        if (count > 0)
            list[strlen(list) - 1] = 0;

        snprintf(msg, sizeof(msg),
                 "SPEC_MOVE|%s|%d|%d|HIT|STATUS=SUNK|%s\n",
                 target_side, x, y, list);
    }
    else
    {
        snprintf(msg, sizeof(msg),
                 "SPEC_MOVE|%s|%d|%d|%s|STATUS=NONE\n",
                 target_side, x, y, result);
    }
    send_to_spectators(g, msg);
    /* ===== GAME OVER ===== */
    // if (!g->alive)
    // {
    //     gs_finish_game(g, sock, "SINK_ALL");
    //     return;
    // }

    /* ===== GAME OVER ===== */
    if (*enemy_remaining <= 0)
    {
        gs_finish_game(g, sock, "SINK_ALL");
        return;
    }

    /* ===== TURN LOGIC ===== */
    g->turn_started_at = time(NULL);

    if (!is_hit)
    {
        g->turn = (g->turn == 1 ? 2 : 1);

        send_logged(sock, "OPPONENT_TURN\n");
        send_logged(enemy_sock, "YOUR_TURN\n");

        snprintf(msg, sizeof(msg),
                 "SPEC_TURN|%s\n",
                 g->turn == 1 ? "P1" : "P2");
        send_to_spectators(g, msg);
    }
    else
    {
        send_logged(sock, "YOUR_TURN\n");
        send_logged(enemy_sock, "OPPONENT_TURN\n");
    }
}

// Handle player disconnect
void gs_handle_disconnect(int sock)
{
    OnlineUser *c = online_user_by_sock(sock);
    if (!c)
        return;

    Game *g = find_game(sock);
    if (!g || !g->alive)
        return;

    // Đã có DC đang chờ xử → bỏ qua
    if (g->dc_sock != 0)
        return;

    int other = (sock == g->p1 ? g->p2 : g->p1);

    // 🔴 ĐÁNH DẤU DC, CHƯA XỬ THUA NGAY
    g->dc_sock = sock;
    g->dc_expire = time(NULL) + 30;

    // ❗ KHÔNG gửi OPPONENT_DISCONNECTED cho player
    // Chỉ gửi cho spectator (nếu có)
    char msg[64];
    snprintf(msg, sizeof(msg),
             "SPEC_DISCONNECT|%s|30\n",
             sock == g->p1 ? "P1" : "P2");
    send_to_spectators(g, msg);

    // Remove khỏi matchmaking
    mm_remove_socket(sock);

    // Reset state user
    c->state = STATE_IDLE;
    c->last_ping = 0;
}

// Check for disconnected players and handle forfeit
void gs_tick_afk(void)
{
    time_t now = time(NULL);

    for (int i = 0; i < game_count; i++)
    {
        Game *g = &games[i];
        if (!g->alive)
            continue;

        // Có player đang bị DC
        if (g->dc_sock != 0 && now >= g->dc_expire)
        {
            int loser = g->dc_sock;
            int winner = (loser == g->p1) ? g->p2 : g->p1;

            gs_finish_game(g, winner, "DISCONNECT");
            g->dc_sock = 0;
        }
    }
}

// Check for turn timeouts
void gs_tick_turn_timeout(void)
{
    time_t now = time(NULL);

    for (int i = 0; i < game_count; i++)
    {
        Game *g = &games[i];
        if (!g->alive)
            continue;

        if (difftime(now, g->turn_started_at) >= 45)
        {
            // đổi lượt
            g->turn = (g->turn == 1 ? 2 : 1);
            g->turn_started_at = now;

            int cur = (g->turn == 1 ? g->p1 : g->p2);
            int other = (g->turn == 1 ? g->p2 : g->p1);

            send_logged(cur, "YOUR_TURN\n");
            send_logged(other, "OPPONENT_TURN\n");

            send_logged(cur, "INFO|Opponent timed out. Your turn.\n");
            send_logged(other, "INFO|You ran out of time. Opponent turn.\n");
        }
    }
}

// Forfeit the game
void gs_forfeit(int sock)
{
    Game *g = find_game(sock);
    if (!g || !g->alive)
        return;

    int is_p1 = (sock == g->p1);
    int winner_sock = is_p1 ? g->p2 : g->p1;

    gs_finish_game(g, winner_sock, "SURRENDER");
}

void gs_handle_leave(int sock)
{
    Game *g = gs_find_by_player(sock);

    if (g)
    {
        if (sock == g->p1) {
            g->left1 = 1;
            g->p1 = 0;   
        }
        else if (sock == g->p2) {
            g->left2 = 1;
            g->p2 = 0;   
        }

        int other = (g->p1 != 0) ? g->p1 : g->p2;
        if (other > 0)
            send_logged(other, "OPPONENT_LEFT\n");

        if (g->left1 && g->left2)
        {
            memset(g, 0, sizeof(Game));
        }
    }

    OnlineUser *u = online_user_by_sock(sock);
    if (u)
        u->state = STATE_IDLE;

    send_logged(sock, "LEFT_GAME\n");
    mm_remove_socket(sock);
}



// xong game thi di qua day de update elo va history
void gs_finish_game(Game *g, int winner_sock, const char *reason)
{
    if (!g || !g->alive)
        return;

    int p1 = g->p1;
    int p2 = g->p2;

    int winner_is_p1 = (winner_sock == p1);
    int loser_sock = winner_is_p1 ? p2 : p1;

    /* ===== ELO + HISTORY ===== */
    int delta_w = 0, delta_l = 0;

    if (g->ranked)
    {
        int Ra = g->elo1, Rb = g->elo2;
        int newRa, newRb;

        if (winner_is_p1)
            elo_update_pair(Ra, Rb, 1, 32, &newRa, &newRb);
        else
            elo_update_pair(Ra, Rb, 0, 32, &newRa, &newRb);

        db_set_elo(g->user1, newRa);
        db_set_elo(g->user2, newRb);

        delta_w = winner_is_p1 ? (newRa - Ra) : (newRb - Rb);
        delta_l = winner_is_p1 ? (newRb - Rb) : (newRa - Ra);
    }

    if (winner_is_p1)
    {
        db_add_history(g->user1, g->user2, "WIN", delta_w);
        db_add_history(g->user2, g->user1, "LOSE", delta_l);
    }
    else
    {
        db_add_history(g->user2, g->user1, "WIN", delta_w);
        db_add_history(g->user1, g->user2, "LOSE", delta_l);
    }

    /* ===== SEND RESULT ===== */
    send_logged(winner_sock, "GAMEOVER|WIN\n");
    send_logged(loser_sock, "GAMEOVER|LOSE\n");

    char msg[128];
    snprintf(msg, sizeof(msg),
             "SPEC_GAMEOVER|WINNER=%s|REASON=%s\n",
             winner_is_p1 ? "P1" : "P2", reason);
    send_to_spectators(g, msg);

    /* ===== RESET PLAYER STATE ===== */
    // OnlineUser *u1 = online_user_by_sock(p1);
    // OnlineUser *u2 = online_user_by_sock(p2);

    // if (u1) u1->state = STATE_IDLE;
    // if (u2) u2->state = STATE_IDLE;

    /* ===== MARK GAME FINISHED (DO NOT DELETE) ===== */
    g->alive = 0;          // game kết thúc
    g->dc_sock = 0;
    g->dc_expire = 0;

    // reset rematch flags cho vòng sau
    g->rematch1 = 0;
    g->rematch2 = 0;

    // KHÔNG:
    //  - reset p1 / p2
    //  - memset game
    //  - cleanup slot ở đây
}


void gs_cleanup_finished_games()
{
    for (int i = 0; i < game_count; i++)
    {
        if (!games[i].alive)
        {
            games[i] = games[game_count - 1];
            game_count--;
            i--;
        }
    }
}

// Send reaction emoji
void gs_send_react(int from_sock, const char *emoji)
{
    int opponent = gs_get_opponent_sock(from_sock);
    if (opponent <= 0)
        return;

    char msg[128];

    snprintf(msg, sizeof(msg), "MY_REACT|%s\n", emoji);
    send_logged(from_sock, msg);

    snprintf(msg, sizeof(msg), "OPPONENT_REACT|%s\n", emoji);
    send_logged(opponent, msg);
}

// Send chat message
void gs_send_chat(int from_sock, const char *msg)
{
    Game *g = find_game(from_sock);
    if (!g || !g->alive)
        return;

    const char *sender =
        (from_sock == g->p1) ? g->user1 : g->user2;

    char buf[512];

    snprintf(buf, sizeof(buf),
             "CHAT|%s|%s\n", sender, msg);
    send_logged(from_sock, buf);

    int opp = gs_get_opponent_sock(from_sock);
    if (opp > 0)
        send_logged(opp, buf);
}

// Add a spectator
int gs_add_spectator(Game *gs, int sock)
{
    if (gs->spectator_count >= MAX_SPECTATORS)
        return -1;

    gs->spectators[gs->spectator_count++] = sock;
    return 0;
}

// Remove a spectator
void gs_remove_spectator(Game *gs, int sock)
{
    for (int i = 0; i < gs->spectator_count; i++)
    {
        if (gs->spectators[i] == sock)
        {
            gs->spectators[i] =
                gs->spectators[--gs->spectator_count];
            return;
        }
    }
}

// Gửi thông báo đến tất cả spectator
static void notify_spectators(Game *gs, const char *msg)
{
    for (int i = 0; i < gs->spectator_count; i++)
    {
        send_logged(gs->spectators[i], msg);
    }
}

// Check if user is in any game
int user_is_in_game(const char *username)
{
    int sock = user_get_sock(username);
    if (sock < 0)
        return 0;

    return gs_find_by_player(sock) != NULL;
}

// Find game session by player socket
Game *gs_find_by_player(int sock)
{
    for (int i = 0; i < game_count; i++)
    {
        Game *gs = &games[i];
        if (gs->alive && (gs->p1 == sock || gs->p2 == sock))
            return gs;
    }
    return NULL;
}

// Check if sock is a player in the game session
int gs_is_player(Game *gs, int sock)
{
    return gs->p1 == sock || gs->p2 == sock;
}

// Check if sock is a spectator in the game session
int gs_is_spectator(Game *gs, int sock)
{
    for (int i = 0; i < gs->spectator_count; i++)
        if (gs->spectators[i] == sock)
            return 1;
    return 0;
}

void send_to_spectators(Game *g, const char *msg)
{
    for (int i = 0; i < g->spectator_count; i++)
    {
        send_logged(g->spectators[i], msg);
    }
}

void build_spec_board(unsigned char *shots, char *out)
{
    for (int i = 0; i < 100; i++)
    {
        if (shots[i] == 'H')
            out[i] = 'H';
        else if (shots[i] == 'M')
            out[i] = 'M';
        else
            out[i] = 'U';
    }
    out[100] = '\0';
}

void gs_send_snapshot_to_spectator(Game *g, int spec_sock)
{
    char board[101];
    char msg[256];

    // P1 board (shots by P2)
    build_spec_board(g->shots_by_p2, board);
    snprintf(msg, sizeof(msg), "SPEC_BOARD|P1|%s\n", board);
    send_logged(spec_sock, msg);

    // P2 board (shots by P1)
    build_spec_board(g->shots_by_p1, board);
    snprintf(msg, sizeof(msg), "SPEC_BOARD|P2|%s\n", board);
    send_logged(spec_sock, msg);

    // Current turn
    snprintf(msg, sizeof(msg),
             "SPEC_TURN|%s\n",
             g->turn == 1 ? "P1" : "P2");
    send_logged(spec_sock, msg);
}

void build_ship_bits(unsigned char *ships, char *out)
{
    for (int i = 0; i < 100; i++)
        out[i] = (ships[i] == 1 || ships[i] == 2) ? '1' : '0';
    out[100] = '\0';
}

void gs_send_ship_snapshot(Game *g, int spec_sock)
{
    char bits[101];
    char msg[256];

    // P1 ships
    build_ship_bits(g->ships1, bits);
    snprintf(msg, sizeof(msg),
             "SPEC_SHIPS|P1|%s\n", bits);
    send_logged(spec_sock, msg);

    // P2 ships
    build_ship_bits(g->ships2, bits);
    snprintf(msg, sizeof(msg),
             "SPEC_SHIPS|P2|%s\n", bits);
    send_logged(spec_sock, msg);
}

/* ===================== REMATCH ===================== */

static void reset_match_state(Game *g, int starting_turn)
{
    g->turn = (starting_turn == 2 ? 2 : 1);
    g->alive = 1;
    g->turn_started_at = time(NULL);

    g->dc_sock = 0;
    g->dc_expire = 0;

    clear_board(g->shots_by_p1, 'U');
    clear_board(g->shots_by_p2, 'U');

    randomize_fleet(g->ships1, &g->remaining1);
    randomize_fleet(g->ships2, &g->remaining2);

    g->rematch1 = 0;
    g->rematch2 = 0;
}

static void send_match_start(Game *g)
{
    /* Send MATCH_FOUND */
    char msg1[128], msg2[128];
    int p1_starts = (g->turn == 1);

    snprintf(msg1, sizeof(msg1),
             "MATCH_FOUND|%s|%d|%d\n",
             g->user2, g->elo2, p1_starts ? 1 : 0);
    snprintf(msg2, sizeof(msg2),
             "MATCH_FOUND|%s|%d|%d\n",
             g->user1, g->elo1, p1_starts ? 0 : 1);

    send_logged(g->p1, msg1);
    send_logged(g->p2, msg2);

    /* Send ships to each player */
    char buf1[CELLS + 1], buf2[CELLS + 1];
    char send1[CELLS + 32], send2[CELLS + 32];

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

    /* Turn signals */
    if (p1_starts)
    {
        send_logged(g->p1, "YOUR_TURN\n");
        send_logged(g->p2, "OPPONENT_TURN\n");
    }
    else
    {
        send_logged(g->p1, "OPPONENT_TURN\n");
        send_logged(g->p2, "YOUR_TURN\n");
    }
}

void gs_accept_rematch(int sock)
{
    Game *g = find_game_any(sock);
    if (!g)
    {
        send_logged(sock, "ERROR|No previous match for rematch\n");
        return;
    }

    if (g->alive)
    {
        send_logged(sock, "ERROR|Match still running\n");
        return;
    }

    int is_p1 = (sock == g->p1);
    const char *who = is_p1 ? g->user1 : g->user2;

    /* Only allow accepting if the opponent already requested. */
    int opponent_requested = is_p1 ? g->rematch2 : g->rematch1;
    if (!opponent_requested)
    {
        send_logged(sock, "ERROR|No rematch request to accept\n");
        return;
    }

    if (is_p1)
        g->rematch1 = 1;
    else
        g->rematch2 = 1;

    printf("[Server] REMATCH accepted by %s (sock=%d)\n", who, sock);
    fflush(stdout);

    char notice[128];
    snprintf(notice, sizeof(notice), "REMATCH_ACCEPTED|%s\n", who);
    if (g->p1 > 0)
        send_logged(g->p1, notice);
    if (g->p2 > 0)
        send_logged(g->p2, notice);

    if (g->rematch1 && g->rematch2)
    {
        /* Refresh ELO in case ranked match changed it */
        g->elo1 = db_get_elo(g->user1);
        g->elo2 = db_get_elo(g->user2);

        int starting_turn = (rand() % 2) ? 1 : 2;
        reset_match_state(g, starting_turn);
        send_match_start(g);
    }
}

void gs_decline_rematch(int sock)
{
    Game *g = find_game_any(sock);
    if (!g)
    {
        send_logged(sock, "ERROR|No previous match for rematch\n");
        return;
    }

    if (g->alive)
    {
        send_logged(sock, "ERROR|Match still running\n");
        return;
    }

    int is_p1 = (sock == g->p1);
    const char *who = is_p1 ? g->user1 : g->user2;

    /* Only allow declining if the opponent already requested. */
    int opponent_requested = is_p1 ? g->rematch2 : g->rematch1;
    if (!opponent_requested)
    {
        send_logged(sock, "ERROR|No rematch request to decline\n");
        return;
    }

    /* Clear pending request */
    g->rematch1 = 0;
    g->rematch2 = 0;

    printf("[Server] REMATCH declined by %s (sock=%d)\n", who, sock);
    fflush(stdout);

    char notice[128];
    snprintf(notice, sizeof(notice), "REMATCH_DECLINED|%s\n", who);
    if (g->p1 > 0)
        send_logged(g->p1, notice);
    if (g->p2 > 0)
        send_logged(g->p2, notice);
}

void gs_request_rematch(int sock)
{
    Game *g = find_game_any(sock);
    if (!g)
    {
        send_logged(sock, "ERROR|No previous match for rematch\n");
        return;
    }

    if (g->alive)
    {
        send_logged(sock, "ERROR|Match still running\n");
        return;
    }

    int is_p1 = (sock == g->p1);
    const char *who = is_p1 ? g->user1 : g->user2;

    /* Backward-compat / convenience:
     * If the opponent already requested a rematch and this player presses "REMATCH",
     * treat it as ACCEPT.
     */
    int opponent_requested = is_p1 ? g->rematch2 : g->rematch1;
    int self_requested = is_p1 ? g->rematch1 : g->rematch2;
    if (opponent_requested && !self_requested)
    {
        gs_accept_rematch(sock);
        return;
    }

    if (self_requested)
    {
        send_logged(sock, "ERROR|Rematch already requested\n");
        return;
    }

    if (is_p1)
        g->rematch1 = 1;
    else
        g->rematch2 = 1;

    /* Requirement: server console should show who pressed rematch */
    printf("[Server] REMATCH requested by %s (sock=%d)\n", who, sock);
    fflush(stdout);

    char notice[128];
    snprintf(notice, sizeof(notice), "REMATCH|%s\n", who);
    if (g->p1 > 0)
        send_logged(g->p1, notice);
    if (g->p2 > 0)
        send_logged(g->p2, notice);
}
