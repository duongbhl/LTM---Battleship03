#include "../include/server.h"
#include "../include/auth.h"
#include "../include/matchmaking.h"
#include "../include/game_session.h"
#include "../include/database.h"
#include "../include/utils.h"
#include "../include/friend.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <unistd.h>
#include <arpa/inet.h>

int listen_sock;

static void *afk_watcher(void *arg)
{
    while (1)
    {
        sleep(1);
        gs_tick_afk();
        gs_tick_turn_timeout();
    }
    return NULL;
}

static void *client_thread(void *arg)
{
    int sock = *(int *)arg;
    free(arg);

    printf("[Server] Client connected: %d\n", sock);

    char buf[256];

    while (1)
    {
        int n = recv(sock, buf, sizeof(buf) - 1, 0);
        fflush(stdout);
        if (n <= 0)
        {
            printf("[Server] Disconnect detected sock=%d\n", sock);

            if (gs_player_in_game(sock) && gs_game_alive(sock))
            {
                printf("[Server] Lost connection: %d → waiting 30 sec...\n", sock);
                gs_handle_disconnect(sock);
                break;
            }

            mm_remove_socket(sock);
            user_set_offline_by_sock(sock);
            close(sock);
            return NULL;
        }

        buf[n] = '\0';
        printf("[RX sock=%d] %s", sock, buf);
        trim_newline(buf);

        // --- PARSE CHUẨN ---
        char cmd[32] = {0}, a[64] = {0}, b[64] = {0};

        char *p1 = strtok(buf, "|");
        char *p2 = strtok(NULL, "|");
        char *p3 = strtok(NULL, "|");

        if (p1)
            strcpy(cmd, p1);
        if (p2)
            strcpy(a, p2);
        if (p3)
            strcpy(b, p3);

        int parts = 0;
        if (p1)
            parts = 1;
        if (p2)
            parts = 2;
        if (p3)
            parts = 3;

        // --------------------

        if (strcmp(cmd, "LOGIN") == 0 && parts == 3)
        {
            handle_login(sock, a, b);
            continue;
        }
        else if (strcmp(cmd, "REGISTER") == 0 && parts == 3)
        {
            handle_register(sock, a, b);
            continue;
        }
        else if (strncmp(cmd, "LOGOUT", 6) == 0)
        {
            handle_logout(sock, a);
        }

        else if (strcmp(cmd, "FIND_MATCH") == 0 && parts >= 3)
        {
            char *username = a;
            char *mode = b; // "rank" hoặc "open"

            int elo = db_get_elo(username);

            if (strcmp(mode, "rank") == 0)
                mm_request_match(sock, username, elo, 1);
            else
                mm_request_match(sock, username, elo, 0);

            continue;
        }

        else if (strcmp(cmd, "MOVE") == 0 && parts == 3)
        {
            int x = atoi(a);
            int y = atoi(b);
            gs_handle_move(sock, x, y);
            continue;
        }
        else if (strcmp(cmd, "FORFEIT") == 0)
        {
            printf("[Server] %d sent FORFEIT\n", sock);
            gs_forfeit(sock);
            continue;
        }
        else if (strcmp(cmd, "SURRENDER") == 0)
        {
            printf("[Server] %d sent SURRENDER\n", sock);
            gs_forfeit(sock);
            continue;
        }
        else if (strcmp(cmd, "GET_HISTORY") == 0 && parts >= 2)
        {
            const char *user = a;

            send_logged(sock, "HISTORY_BEGIN\n");
            db_get_history(user, sock);
            send_logged(sock, "HISTORY_END\n");
        }

        else if (strcmp(cmd, "REACT") == 0 && parts >= 2)
        {
            // a = emoji
            gs_send_react(sock, a);
            continue;
        }

        else if (strcmp(cmd, "CHAT") == 0 && parts >= 2)
        {
            gs_send_chat(sock, a);
            continue;
        }
        else if (strcmp(cmd, "FRIEND_REQUEST") == 0 && parts == 3)
        {
            // a = from, b = to
            handle_friend_request(sock, a, b);
            continue;
        }

        else if (strcmp(cmd, "FRIEND_ACCEPT") == 0 && parts == 3)
        {
            // a = me, b = other
            handle_friend_accept(sock, a, b);
            continue;
        }

        else if (strcmp(cmd, "FRIEND_REJECT") == 0 && parts == 3)
        {
            // a = me, b = other
            handle_friend_reject(sock, a, b);
            continue;
        }

        else if (strcmp(cmd, "GET_FRIENDS_ONLINE") == 0 && parts >= 2)
        {
            // a = username
            handle_get_friends_online(sock, a);
            continue;
        }

        else if (strcmp(cmd, "GET_ONLINE") == 0)
        {
            char list[512];
            char msg[600];

            user_get_all(list, sizeof(list));
            snprintf(msg, sizeof(msg), "ONLINE_LIST|%s\n", list);
            send_logged(sock, msg);
            continue;
        }
        else
        {
            send_all(sock, "ERROR|Unknown command\n", 23);
        }
    }

    close(sock);
    return NULL;
}

void server_init(int port)
{
    listen_sock = socket(AF_INET, SOCK_STREAM, 0);

    int opt = 1;
    setsockopt(listen_sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(port);

    bind(listen_sock, (struct sockaddr *)&addr, sizeof(addr));
    listen(listen_sock, 20);

    printf("[Main] Database ready.\n");
    printf("[Server] Listening on port %d...\n", port);
    pthread_t afk;
    pthread_create(&afk, NULL, afk_watcher, NULL);
    pthread_detach(afk);
}

void server_run()
{
    while (1)
    {
        int client = accept(listen_sock, NULL, NULL);
        int *p = malloc(sizeof(int));
        *p = client;

        pthread_t t;
        pthread_create(&t, NULL, client_thread, p);
        pthread_detach(t);
    }
}
