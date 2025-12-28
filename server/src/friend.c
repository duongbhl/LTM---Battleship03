#include "../include/friend.h"
#include "../include/database.h"
#include "../include/online_users.h"
#include "../include/game_session.h"
#include "../include/matchmaking.h"
#include "../include/utils.h"
#include <string.h>
#include <stdio.h>

/* ===================== CHALLENGE (ELO) =====================
 * Lightweight in-memory challenge handshake:
 *  - A sends CHALLENGE_ELO|A|B
 *  - B receives CHALLENGE_INVITE|A
 *  - B replies CHALLENGE_ACCEPT|B|A or CHALLENGE_DECLINE|B|A
 * Server then starts a ranked game session (ELO).
 */

typedef struct {
    int active;
    int challenger_sock;
    int target_sock;
    char challenger[32];
    char target[32];
} Challenge;

#define MAX_CHALLENGES 200
static Challenge g_challenges[MAX_CHALLENGES];

static Challenge* find_challenge_by_target_sock(int target_sock)
{
    for (int i = 0; i < MAX_CHALLENGES; i++) {
        if (g_challenges[i].active && g_challenges[i].target_sock == target_sock)
            return &g_challenges[i];
    }
    return NULL;
}

static Challenge* find_challenge_by_pair(int challenger_sock, int target_sock)
{
    for (int i = 0; i < MAX_CHALLENGES; i++) {
        if (g_challenges[i].active &&
            g_challenges[i].challenger_sock == challenger_sock &&
            g_challenges[i].target_sock == target_sock)
            return &g_challenges[i];
    }
    return NULL;
}

static Challenge* alloc_challenge(void)
{
    for (int i = 0; i < MAX_CHALLENGES; i++) {
        if (!g_challenges[i].active) {
            memset(&g_challenges[i], 0, sizeof(g_challenges[i]));
            g_challenges[i].active = 1;
            return &g_challenges[i];
        }
    }
    return NULL;
}

static void clear_challenge(Challenge* c)
{
    if (!c) return;
    memset(c, 0, sizeof(*c));
}

// void handle_friend_request(int sock, const char *from, const char *to)
// {
//     // chỉ check user tồn tại
//     if (!db_user_exists(to))
//     {
//         send_logged(sock, "ERROR|User does not exist\n");
//         return;
//     }

//     db_insert_friend_request(from, to);

//     int to_sock = user_get_sock(to);
//     // if (to_sock >= 0)
//     // {
//     //     char msg[128];
//     //     snprintf(msg, sizeof(msg), "FRIEND_INVITE|%s\n", from);
//     //     send_logged(to_sock, msg);
//     // }

//     char msg[128];
//     snprintf(msg, sizeof(msg), "FRIEND_INVITE|%s\n", from);
//     send_logged(1, msg);
// }


void handle_friend_request(int sock, const char *from, const char *to)
{
    if (!db_user_exists(to)) {
        send_logged(sock, "ERROR|User does not exist\n");
        return;
    }

    // luôn lưu (online/offline đều lưu)
    db_insert_friend_request(from, to);

    // báo lại cho người gửi để UI hiện "đã gửi"
    {
        char ok[128];
        snprintf(ok, sizeof(ok), "FRIEND_SENT|%s\n", to);
        send_logged(sock, ok);
    }

    // nếu người nhận đang online thì push realtime
    int to_sock = user_get_sock(to);
    if (to_sock >= 0) {
        char msg[128];
        snprintf(msg, sizeof(msg), "FRIEND_INVITE|%s\n", from);
        send_logged(to_sock, msg);
    }
}


void handle_friend_accept(int sock, const char *me, const char *other)
{
    if (!db_friend_request_exists(other, me))
    {
        send_logged(sock, "ERROR|No friend request\n");
        return;
    }

    db_accept_friend(other, me);

    send_logged(sock, "FRIEND_ACCEPTED\n");

    int other_sock = user_get_sock(other);
    if (other_sock >= 0)
    {
        char msg[64];
        snprintf(msg, sizeof(msg), "FRIEND_ACCEPTED|%s\n", me);
        send_logged(other_sock, msg);
    }
}

void handle_friend_reject(int sock, const char *me, const char *other)
{
    db_delete_friend(me, other);
    send_logged(sock, "FRIEND_REJECTED\n");
}

void handle_get_friends_online(int sock, const char *user)
{
    char friends[64][32];
    int n = db_get_accepted_friends(user, friends, 64);

    char out[1024] = "";
    for (int i = 0; i < n; i++)
    {
        if (user_is_online(friends[i]))
        {
            strcat(out, friends[i]);
            strcat(out, ",");
        }
    }

    char msg[1100];
    snprintf(msg, sizeof(msg), "FRIENDS_ONLINE|%s\n", out);
    send_logged(sock, msg);
}

/* ===================== CHALLENGE (ELO) ===================== */

void handle_challenge_elo(int sock, const char *from, const char *to)
{
    if (!from || !to || from[0] == '\0' || to[0] == '\0') {
        send_logged(sock, "ERROR|Invalid challenge\n");
        return;
    }

    if (strcmp(from, to) == 0) {
        send_logged(sock, "ERROR|Cannot challenge yourself\n");
        return;
    }

    int to_sock = user_get_sock(to);
    if (to_sock < 0) {
        send_logged(sock, "ERROR|User not online\n");
        return;
    }

    /* Don't allow challenges if either player is in a live game or queue */
    if (gs_player_in_game(sock) || gs_player_in_game(to_sock)) {
        send_logged(sock, "ERROR|Player already in game\n");
        return;
    }

    if (mm_player_waiting(sock) || mm_player_waiting(to_sock)) {
        send_logged(sock, "ERROR|Player currently in queue\n");
        return;
    }

    /* Only 1 pending challenge per target (simple & predictable) */
    if (find_challenge_by_target_sock(to_sock)) {
        send_logged(sock, "ERROR|Target already has a pending challenge\n");
        return;
    }

    Challenge *c = alloc_challenge();
    if (!c) {
        send_logged(sock, "ERROR|Too many pending challenges\n");
        return;
    }

    c->challenger_sock = sock;
    c->target_sock = to_sock;
    strncpy(c->challenger, from, sizeof(c->challenger) - 1);
    strncpy(c->target, to, sizeof(c->target) - 1);

    printf("[Server] CHALLENGE_ELO requested: %s (sock=%d) -> %s (sock=%d)\n",
           c->challenger, c->challenger_sock, c->target, c->target_sock);
    fflush(stdout);

    /* Notify both sides */
    {
        char ok[128];
        snprintf(ok, sizeof(ok), "CHALLENGE_SENT|%s\n", to);
        send_logged(sock, ok);
    }
    {
        char msg[128];
        snprintf(msg, sizeof(msg), "CHALLENGE_INVITE|%s\n", from);
        send_logged(to_sock, msg);
    }
}

void handle_challenge_accept(int sock, const char *me, const char *other)
{
    (void)me;

    Challenge *c = find_challenge_by_target_sock(sock);
    if (!c) {
        send_logged(sock, "ERROR|No pending challenge\n");
        return;
    }

    /* Optional safety: ensure the accept references the same challenger */
    if (other && other[0] != '\0' && strcmp(c->challenger, other) != 0) {
        send_logged(sock, "ERROR|Challenge mismatch\n");
        return;
    }

    int challenger_sock = c->challenger_sock;
    int target_sock = c->target_sock;

    /* If challenger disconnected, reject and clear */
    if (challenger_sock <= 0 || user_get_sock(c->challenger) != challenger_sock) {
        send_logged(sock, "ERROR|Challenger is no longer online\n");
        clear_challenge(c);
        return;
    }

    /* Re-check states */
    if (gs_player_in_game(challenger_sock) || gs_player_in_game(target_sock)) {
        send_logged(sock, "ERROR|Player already in game\n");
        clear_challenge(c);
        return;
    }
    if (mm_player_waiting(challenger_sock) || mm_player_waiting(target_sock)) {
        send_logged(sock, "ERROR|Player currently in queue\n");
        clear_challenge(c);
        return;
    }

    char challenger_user[32];
    char target_user[32];
    strncpy(challenger_user, c->challenger, sizeof(challenger_user) - 1);
    challenger_user[sizeof(challenger_user) - 1] = '\0';
    strncpy(target_user, c->target, sizeof(target_user) - 1);
    target_user[sizeof(target_user) - 1] = '\0';

    printf("[Server] CHALLENGE_ELO accepted by %s (sock=%d) vs %s (sock=%d)\n",
           target_user, target_sock, challenger_user, challenger_sock);
    fflush(stdout);

    /* Start ranked session using latest ELO */
    int elo_a = db_get_elo(challenger_user);
    int elo_b = db_get_elo(target_user);

    /* Clear first to avoid re-entrancy issues */
    clear_challenge(c);

    gs_create_session(challenger_sock, challenger_user, elo_a,
                      target_sock, target_user, elo_b,
                      1);
}

void handle_challenge_decline(int sock, const char *me, const char *other)
{
    (void)me;

    Challenge *c = find_challenge_by_target_sock(sock);
    if (!c) {
        send_logged(sock, "ERROR|No pending challenge\n");
        return;
    }

    if (other && other[0] != '\0' && strcmp(c->challenger, other) != 0) {
        send_logged(sock, "ERROR|Challenge mismatch\n");
        return;
    }

    printf("[Server] CHALLENGE_ELO declined by %s (sock=%d) vs %s (sock=%d)\n",
           c->target, c->target_sock, c->challenger, c->challenger_sock);
    fflush(stdout);

    /* Notify both sides */
    {
        char msg[128];
        snprintf(msg, sizeof(msg), "CHALLENGE_DECLINED|%s\n", c->target);
        if (c->challenger_sock > 0)
            send_logged(c->challenger_sock, msg);
        if (c->target_sock > 0)
            send_logged(c->target_sock, msg);
    }

    clear_challenge(c);
}

void handle_challenge_cancel(int sock, const char *from, const char *to)
{
    if (!from || !to) {
        send_logged(sock, "ERROR|Invalid challenge cancel\n");
        return;
    }

    int to_sock = user_get_sock(to);
    if (to_sock < 0) {
        /* Target offline: still remove any pending pair */
        for (int i = 0; i < MAX_CHALLENGES; i++) {
            if (g_challenges[i].active &&
                g_challenges[i].challenger_sock == sock &&
                strcmp(g_challenges[i].challenger, from) == 0 &&
                strcmp(g_challenges[i].target, to) == 0)
            {
                clear_challenge(&g_challenges[i]);
                send_logged(sock, "CHALLENGE_CANCELLED\n");
                return;
            }
        }
        send_logged(sock, "ERROR|No pending challenge to cancel\n");
        return;
    }

    Challenge *c = find_challenge_by_pair(sock, to_sock);
    if (!c) {
        send_logged(sock, "ERROR|No pending challenge to cancel\n");
        return;
    }

    printf("[Server] CHALLENGE_ELO cancelled by %s (sock=%d) -> %s (sock=%d)\n",
           c->challenger, c->challenger_sock, c->target, c->target_sock);
    fflush(stdout);

    {
        char msg[128];
        snprintf(msg, sizeof(msg), "CHALLENGE_CANCELLED|%s\n", from);
        if (c->target_sock > 0)
            send_logged(c->target_sock, msg);
        send_logged(sock, "CHALLENGE_CANCELLED\n");
    }

    clear_challenge(c);
}

