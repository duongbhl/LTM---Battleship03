#include "../include/matchmaking.h"
#include "../include/game_session.h"
#include "../include/utils.h"

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <pthread.h>

#define MAXQ 100

typedef struct {
    int sock;
    char user[32];
    int elo;
} Player;

/* HÀNG ĐỢI OPEN RANK */
static Player Q_open[MAXQ];
static int q_open_len = 0;

/* HÀNG ĐỢI ELO RANK */
static Player Q_elo[MAXQ];
static int q_elo_len = 0;

static pthread_mutex_t mm_lock = PTHREAD_MUTEX_INITIALIZER;


/********************************************************************
 * GHÉP TRẬN OPEN RANK – chỉ cần có 2 người → ghép ngay
 ********************************************************************/
static void match_open_rank(int sock, const char *user, int elo)
{
    if (q_open_len == 0)
    {
        /* chưa có ai → đưa vào hàng */
        Q_open[0].sock = sock;
        strcpy(Q_open[0].user, user);
        Q_open[0].elo = elo;
        q_open_len = 1;

        send_all(sock, "QUEUED|Waiting opponent...\n", 28);
        return;
    }

    /* đã có người chờ → ghép */
    Player p = Q_open[0];

    /* shift queue */
    for (int i = 1; i < q_open_len; i++)
        Q_open[i - 1] = Q_open[i];
    q_open_len--;

    printf("[MM][OPEN] Match found: %s vs %s\n", p.user, user);

    gs_create_session(
        p.sock, p.user, p.elo,
        sock, user, elo
    );
}


/********************************************************************
 * GHÉP TRẬN ELO RANK – tìm người có ELO gần nhất
 ********************************************************************/
static void match_elo_rank(int sock, const char *user, int elo)
{
    if (q_elo_len == 0)
    {
        Q_elo[0].sock = sock;
        strcpy(Q_elo[0].user, user);
        Q_elo[0].elo = elo;
        q_elo_len = 1;

        send_all(sock, "QUEUED|Waiting similar ELO opponent...\n", 40);
        return;
    }

    /* tìm người có elo gần nhất */
    int best = 0;
    int best_diff = abs(Q_elo[0].elo - elo);

    for (int i = 1; i < q_elo_len; i++)
    {
        int diff = abs(Q_elo[i].elo - elo);
        if (diff < best_diff)
        {
            best = i;
            best_diff = diff;
        }
    }

    Player p = Q_elo[best];

    /* xóa khỏi queue */
    for (int i = best + 1; i < q_elo_len; i++)
        Q_elo[i - 1] = Q_elo[i];
    q_elo_len--;

    printf("[MM][ELO] Match found: %s (ELO %d) vs %s (ELO %d)\n",
           p.user, p.elo, user, elo);

    gs_create_session(
        p.sock, p.user, p.elo,
        sock, user, elo
    );
}


/********************************************************************
 * ENTRYPOINT CHÍNH ĐƯỢC GỌI TỪ SERVER
 ********************************************************************/
void mm_request_match(int sock, const char *user, int elo, int elo_mode)
{
    pthread_mutex_lock(&mm_lock);

    if (elo_mode == 1)
        match_elo_rank(sock, user, elo);
    else
        match_open_rank(sock, user, elo);

    pthread_mutex_unlock(&mm_lock);
}
