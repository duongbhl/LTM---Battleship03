#include "../include/friend.h"
#include "../include/database.h"
#include "../include/online_users.h"
#include "../include/game_session.h"
#include "../include/matchmaking.h"
#include "../include/utils.h"
#include "../include/game_session.h"
#include <string.h>
#include <stdio.h>
#include <pthread.h>

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
static pthread_mutex_t g_challenges_mutex = PTHREAD_MUTEX_INITIALIZER;

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

static Challenge* find_challenge_by_target_and_challenger(int target_sock, const char* challenger_user)
{
    if (!challenger_user) return NULL;
    for (int i = 0; i < MAX_CHALLENGES; i++) {
        if (g_challenges[i].active &&
            g_challenges[i].target_sock == target_sock &&
            strcmp(g_challenges[i].challenger, challenger_user) == 0)
        {
            return &g_challenges[i];
        }
    }
    return NULL;
}

static Challenge* find_challenge_by_users(const char* challenger_user, const char* target_user)
{
    if (!challenger_user || !target_user) return NULL;
    for (int i = 0; i < MAX_CHALLENGES; i++) {
        if (g_challenges[i].active &&
            strcmp(g_challenges[i].challenger, challenger_user) == 0 &&
            strcmp(g_challenges[i].target, target_user) == 0)
        {
            return &g_challenges[i];
        }
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

void handle_friend_request(int sock, const char *from, const char *to)
{
    if (!db_user_exists(to))
    {
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
    if (to_sock >= 0)
    {
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
    char buf[64];

    for (int i = 0; i < n; i++)
    {
        if (!user_is_online(friends[i]))
            continue;

        const char *state = user_is_in_game(friends[i])
                                ? "INGAME"
                                : "IDLE";

        snprintf(buf, sizeof(buf), "%s|%s;", friends[i], state);
        strcat(out, buf);
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

    Challenge *c = NULL;

    /* Allow multiple challengers to invite the same target.
     * Prevent duplicates from the same challenger to the same target.
     * NOTE: protect shared g_challenges with a mutex because multiple client
     * threads can send challenges concurrently. */
    pthread_mutex_lock(&g_challenges_mutex);
    if (find_challenge_by_users(from, to)) {
        pthread_mutex_unlock(&g_challenges_mutex);
        send_logged(sock, "ERROR|Challenge already pending\n");
        return;
    }

    c = alloc_challenge();
    if (!c) {
        pthread_mutex_unlock(&g_challenges_mutex);
        send_logged(sock, "ERROR|Too many pending challenges\n");
        return;
    }

    c->challenger_sock = sock;
    c->target_sock = to_sock;
    strncpy(c->challenger, from, sizeof(c->challenger) - 1);
    strncpy(c->target, to, sizeof(c->target) - 1);
    pthread_mutex_unlock(&g_challenges_mutex);

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

    if (!other || other[0] == '\0') {
        send_logged(sock, "ERROR|Invalid challenge accept\n");
        return;
    }

    int challenger_sock = -1;
    int target_sock = sock;
    char challenger_user[32] = {0};
    char target_user[32] = {0};

    /* When target accepts one of many pending challenges, we will
     * auto-decline all other challengers (so they get a clear UI signal).
     * Store them locally then notify after releasing the mutex. */
    int other_socks[MAX_CHALLENGES];
    char other_users[MAX_CHALLENGES][32];
    int other_count = 0;

    pthread_mutex_lock(&g_challenges_mutex);

    Challenge *c = find_challenge_by_target_and_challenger(sock, other);
    if (!c) {
        pthread_mutex_unlock(&g_challenges_mutex);
        send_logged(sock, "ERROR|No pending challenge\n");
        return;
    }

    challenger_sock = c->challenger_sock;
    target_sock = c->target_sock;

    /* If challenger disconnected, reject and clear */
    if (challenger_sock <= 0 || user_get_sock(c->challenger) != challenger_sock) {
        clear_challenge(c);
        pthread_mutex_unlock(&g_challenges_mutex);
        send_logged(sock, "ERROR|Challenger is no longer online\n");
        return;
    }

    /* Re-check states */
    if (gs_player_in_game(challenger_sock) || gs_player_in_game(target_sock)) {
        clear_challenge(c);
        pthread_mutex_unlock(&g_challenges_mutex);
        send_logged(sock, "ERROR|Player already in game\n");
        return;
    }
    if (mm_player_waiting(challenger_sock) || mm_player_waiting(target_sock)) {
        clear_challenge(c);
        pthread_mutex_unlock(&g_challenges_mutex);
        send_logged(sock, "ERROR|Player currently in queue\n");
        return;
    }

    strncpy(challenger_user, c->challenger, sizeof(challenger_user) - 1);
    challenger_user[sizeof(challenger_user) - 1] = '\0';
    strncpy(target_user, c->target, sizeof(target_user) - 1);
    target_user[sizeof(target_user) - 1] = '\0';

    /* Collect + clear all other pending challenges to the same target */
    for (int i = 0; i < MAX_CHALLENGES; i++) {
        if (g_challenges[i].active &&
            g_challenges[i].target_sock == target_sock &&
            &g_challenges[i] != c)
        {
            if (other_count < MAX_CHALLENGES) {
                other_socks[other_count] = g_challenges[i].challenger_sock;
                strncpy(other_users[other_count], g_challenges[i].challenger, 31);
                other_users[other_count][31] = '\0';
                other_count++;
            }
            clear_challenge(&g_challenges[i]);
        }
    }

    /* Clear accepted challenge before releasing lock */
    clear_challenge(c);
    pthread_mutex_unlock(&g_challenges_mutex);

    printf("[Server] CHALLENGE_ELO accepted: %s (sock=%d) vs %s (sock=%d)\n",
           target_user, target_sock, challenger_user, challenger_sock);
    fflush(stdout);

    /* Auto-decline all other challengers */
    for (int i = 0; i < other_count; i++) {
        int csock = other_socks[i];
        if (csock > 0) {
            char msg[160];
            snprintf(msg, sizeof(msg), "CHALLENGE_DECLINED|%s\n", target_user);
            send_logged(csock, msg);
        }
        printf("[Server] CHALLENGE_ELO auto-declined: %s declined %s (sock=%d)\n",
               target_user, other_users[i], csock);
        fflush(stdout);
    }

    /* Start ranked session using latest ELO */
    int elo_a = db_get_elo(challenger_user);
    int elo_b = db_get_elo(target_user);

    gs_create_session(challenger_sock, challenger_user, elo_a,
                      target_sock, target_user, elo_b,
                      1);
}



void handle_challenge_decline(int sock, const char *me, const char *other)
{
    (void)me;

    if (!other || other[0] == '\0') {
        send_logged(sock, "ERROR|Invalid challenge decline\n");
        return;
    }

    int challenger_sock = -1;
    int target_sock = sock;
    char target_user[32] = {0};
    char challenger_user[32] = {0};

    pthread_mutex_lock(&g_challenges_mutex);
    Challenge *c = find_challenge_by_target_and_challenger(sock, other);
    if (!c) {
        pthread_mutex_unlock(&g_challenges_mutex);
        send_logged(sock, "ERROR|No pending challenge\n");
        return;
    }

    challenger_sock = c->challenger_sock;
    target_sock = c->target_sock;
    strncpy(target_user, c->target, sizeof(target_user) - 1);
    target_user[sizeof(target_user) - 1] = '\0';
    strncpy(challenger_user, c->challenger, sizeof(challenger_user) - 1);
    challenger_user[sizeof(challenger_user) - 1] = '\0';

    clear_challenge(c);
    pthread_mutex_unlock(&g_challenges_mutex);

    printf("[Server] CHALLENGE_ELO declined: %s (sock=%d) vs %s (sock=%d)\n",
           target_user, target_sock, challenger_user, challenger_sock);
    fflush(stdout);

    /* Notify both sides */
    {
        char msg[160];
        snprintf(msg, sizeof(msg), "CHALLENGE_DECLINED|%s\n", target_user);
        if (challenger_sock > 0)
            send_logged(challenger_sock, msg);
        if (target_sock > 0)
            send_logged(target_sock, msg);
    }
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
        pthread_mutex_lock(&g_challenges_mutex);
        for (int i = 0; i < MAX_CHALLENGES; i++) {
            if (g_challenges[i].active &&
                g_challenges[i].challenger_sock == sock &&
                strcmp(g_challenges[i].challenger, from) == 0 &&
                strcmp(g_challenges[i].target, to) == 0)
            {
                clear_challenge(&g_challenges[i]);
                pthread_mutex_unlock(&g_challenges_mutex);
                send_logged(sock, "CHALLENGE_CANCELLED\n");
                return;
            }
        }
        pthread_mutex_unlock(&g_challenges_mutex);
        send_logged(sock, "ERROR|No pending challenge to cancel\n");
        return;
    }

    int target_sock = to_sock;
    int challenger_sock = -1;
    char target_user[32] = {0};
    char challenger_user[32] = {0};

    pthread_mutex_lock(&g_challenges_mutex);
    Challenge *c = find_challenge_by_pair(sock, to_sock);
    if (!c) {
        pthread_mutex_unlock(&g_challenges_mutex);
        send_logged(sock, "ERROR|No pending challenge to cancel\n");
        return;
    }

    challenger_sock = c->challenger_sock;
    target_sock = c->target_sock;
    strncpy(target_user, c->target, sizeof(target_user) - 1);
    target_user[sizeof(target_user) - 1] = '\0';
    strncpy(challenger_user, c->challenger, sizeof(challenger_user) - 1);
    challenger_user[sizeof(challenger_user) - 1] = '\0';

    clear_challenge(c);
    pthread_mutex_unlock(&g_challenges_mutex);

    printf("[Server] CHALLENGE_ELO cancelled by %s (sock=%d) -> %s (sock=%d)\n",
           challenger_user, challenger_sock, target_user, target_sock);
    fflush(stdout);

    {
        char msg[128];
        snprintf(msg, sizeof(msg), "CHALLENGE_CANCELLED|%s\n", from);
        if (target_sock > 0)
            send_logged(target_sock, msg);
        send_logged(sock, "CHALLENGE_CANCELLED\n");
    }
}


void handle_watch_friend(int sock, const char *friend)
{
    int fsock = user_get_sock(friend);
    if (fsock < 0) {
        send_logged(sock, "ERROR|Friend not online\n");
        return;
    }

    Game *gs = gs_find_by_player(fsock);
    if (!gs) {
        send_logged(sock, "ERROR|Friend not in game\n");
        return;
    }

    // add spectator
    if (gs->spectator_count < MAX_SPECTATORS) {
        gs->spectators[gs->spectator_count++] = sock;
    }

    // ❗ báo cho client spectator biết vào game ngay
    send_logged(sock, "SPECTATOR_START|\n");

    // gửi snapshot ban đầu
    gs_send_snapshot_to_spectator(gs,sock);

    //gui tau cho spectator
    gs_send_ship_snapshot(gs, sock);  
}

