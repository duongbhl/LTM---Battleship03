#include "../include/matchmaking.h"
#include "../include/game_session.h"
#include "../include/utils.h"

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <pthread.h>
#include <time.h>
#include <unistd.h>

#define MAXQ 100

typedef struct {
    int sock;
    char user[32];
    int elo;
    time_t enqueued_at;
} Player;

/* queues */
static Player Q_open[MAXQ];
static int q_open_len = 0;

static Player Q_elo[MAXQ];
static int q_elo_len = 0;

/* sync */
static pthread_mutex_t mm_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t  mm_cv   = PTHREAD_COND_INITIALIZER;

/* worker */
static pthread_t mm_thread;
static int mm_running = 0;

static int wait_seconds(const Player *p) {
    return (int)difftime(time(NULL), p->enqueued_at);
}

/* window theo thời gian chờ */
static int elo_window_for_wait(int sec) {
    if (sec < 10) return 200;
    if (sec < 20) return 400;
    if (sec < 30) return 800;
    return 999999;
}

/* remove player at index from queue (shift left) */
static void remove_at(Player *Q, int *len, int idx) {
    for (int i = idx + 1; i < *len; i++) Q[i - 1] = Q[i];
    (*len)--;
}

static void match_open_rank_locked(Player me) {
    if (q_open_len == 0) {
        Q_open[0] = me;
        q_open_len = 1;
        send_logged(me.sock, "QUEUED|Waiting opponent...\n");
        printf("[MM][OPEN] queued: %s (sock=%d)\n", me.user, me.sock);
        fflush(stdout);
        return;
    }

    Player p = Q_open[0];
    remove_at(Q_open, &q_open_len, 0);

    printf("[MM][OPEN] Match found: %s vs %s\n", p.user, me.user);
    fflush(stdout);

    gs_create_session(p.sock, p.user, p.elo, me.sock, me.user, me.elo);
}

/* Try to match in ELO queue using dynamic windows.
   Return 1 if a match occurred, else 0. */
static int try_match_elo_locked(void) {
    if (q_elo_len < 2) return 0;

    /* chọn cặp có diff nhỏ nhất trong các cặp "hợp lệ theo window" */
    int best_i = -1, best_j = -1;
    int best_diff = 0;

    for (int i = 0; i < q_elo_len; i++) {
        int wi = wait_seconds(&Q_elo[i]);
        if (wi >= 30) continue; // sẽ sweep sang open ở bước khác

        int window_i = elo_window_for_wait(wi);

        for (int j = i + 1; j < q_elo_len; j++) {
            int wj = wait_seconds(&Q_elo[j]);
            if (wj >= 30) continue;

            int window_j = elo_window_for_wait(wj);
            int allowed = (window_i > window_j ? window_i : window_j);

            int diff = abs(Q_elo[i].elo - Q_elo[j].elo);
            if (diff > allowed) continue;

            if (best_i == -1 || diff < best_diff) {
                best_i = i; best_j = j; best_diff = diff;
            }
        }
    }

    if (best_i == -1) return 0;

    Player a = Q_elo[best_i];
    Player b = Q_elo[best_j];

    /* remove higher index first */
    if (best_j > best_i) {
        remove_at(Q_elo, &q_elo_len, best_j);
        remove_at(Q_elo, &q_elo_len, best_i);
    } else {
        remove_at(Q_elo, &q_elo_len, best_i);
        remove_at(Q_elo, &q_elo_len, best_j);
    }

    printf("[MM][ELO] Match found (diff=%d): %s(%d) vs %s(%d)\n",
           best_diff, a.user, a.elo, b.user, b.elo);
    fflush(stdout);

    gs_create_session(a.sock, a.user, a.elo, b.sock, b.user, b.elo);
    return 1;
}

/* Move ELO-wait>=30s players to open queue (and possibly match there) */
static int sweep_elo_timeouts_locked(void) {
    int moved = 0;
    int i = 0;
    while (i < q_elo_len) {
        int w = wait_seconds(&Q_elo[i]);
        if (w >= 30) {
            Player p = Q_elo[i];
            remove_at(Q_elo, &q_elo_len, i);

            send_logged(p.sock, "QUEUED|No close ELO match. Switching to OPEN queue...\n");
            printf("[MM][ELO] timeout>=30s -> OPEN: %s (elo=%d, sock=%d)\n",
                   p.user, p.elo, p.sock);
            fflush(stdout);

            /* đưa sang open và match ngay nếu được */
            match_open_rank_locked(p);
            moved++;
            continue; // không i++
        }
        i++;
    }
    return moved;
}

static void* mm_worker(void *arg) {
    (void)arg;

    pthread_mutex_lock(&mm_lock);
    while (mm_running) {
        /* chờ signal hoặc timeout 1s để sweep */
        struct timespec ts;
        clock_gettime(0, &ts);
        ts.tv_sec += 1;

        pthread_cond_timedwait(&mm_cv, &mm_lock, &ts);

        if (!mm_running) break;

        /* 1) sweep timeouts */
        sweep_elo_timeouts_locked();

        /* 2) match elo nhiều lần nếu có thể */
        while (try_match_elo_locked()) {
            /* loop */
        }

        /* 3) open queue tự match theo kiểu cặp (nếu muốn) — open rank hiện match khi enqueue,
              nhưng nếu bạn muốn “worker-only”, có thể thêm loop ở đây. */
    }

    pthread_mutex_unlock(&mm_lock);
    return NULL;
}

int mm_player_waiting(int sock) {
    for (int i = 0; i < q_open_len; i++)
        if (Q_open[i].sock == sock) return 1;
    for (int i = 0; i < q_elo_len; i++)
        if (Q_elo[i].sock == sock) return 1;
    return 0;
}

void mm_remove_socket(int sock) {
    pthread_mutex_lock(&mm_lock);

    // remove from OPEN queue
    for (int i = 0; i < q_open_len; ) {
        if (Q_open[i].sock == sock) {
            remove_at(Q_open, &q_open_len, i);
        } else {
            i++;
        }
    }

    // remove from ELO queue
    for (int i = 0; i < q_elo_len; ) {
        if (Q_elo[i].sock == sock) {
            remove_at(Q_elo, &q_elo_len, i);
        } else {
            i++;
        }
    }

    pthread_mutex_unlock(&mm_lock);
}


/* Public: start/stop worker */
void mm_start_worker(void) {
    pthread_mutex_lock(&mm_lock);
    if (mm_running) { pthread_mutex_unlock(&mm_lock); return; }
    mm_running = 1;
    pthread_mutex_unlock(&mm_lock);

    pthread_create(&mm_thread, NULL, mm_worker, NULL);
    pthread_detach(mm_thread);

    printf("[MM] worker started\n");
    fflush(stdout);
}

void mm_stop_worker(void) {
    pthread_mutex_lock(&mm_lock);
    mm_running = 0;
    pthread_cond_broadcast(&mm_cv);
    pthread_mutex_unlock(&mm_lock);
}

/********************************************************************
 * ENTRYPOINT từ server: enqueue, worker lo phần còn lại
 ********************************************************************/
void mm_request_match(int sock, const char *user, int elo, int elo_mode)
{
    Player me;
    me.sock = sock;
    strncpy(me.user, user, sizeof(me.user) - 1);
    me.user[sizeof(me.user) - 1] = '\0';
    me.elo = elo;
    me.enqueued_at = time(NULL);

    pthread_mutex_lock(&mm_lock);

    if (elo_mode == 1) {
        if (q_elo_len < MAXQ) {
            Q_elo[q_elo_len++] = me;
        }
        send_logged(sock, "QUEUED|Waiting similar ELO opponent...\n");
        printf("[MM][ELO] queued: %s (elo=%d, sock=%d)\n", me.user, me.elo, me.sock);
    } else {
        match_open_rank_locked(me); /* open match ngay */
    }

    fflush(stdout);

    /* báo worker có việc */
    pthread_cond_signal(&mm_cv);
    pthread_mutex_unlock(&mm_lock);
}
