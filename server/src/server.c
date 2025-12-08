#include "../include/server.h"
#include "../include/auth.h"
#include "../include/matchmaking.h"
#include "../include/game_session.h"
#include "../include/database.h"
#include "../include/utils.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <unistd.h>
#include <arpa/inet.h>

int listen_sock;

static void *client_thread(void *arg)
{
    int sock = *(int *)arg;
    free(arg);

    printf("[Server] Client connected: %d\n", sock);

    char buf[256];

    while (1)
    {
        int n = recv(sock, buf, sizeof(buf) - 1, 0);
        if (n <= 0) {
            printf("[Server] Lost connection: %d → waiting 30 sec for reconnect...\n", sock);
            gs_handle_disconnect(sock);
            break;
        }
        buf[n] = '\0';
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

        else if (strcmp(cmd, "BOARD") == 0) {
            gs_set_board(sock, a); 
            continue;
        }


        else if (strcmp(cmd, "MOVE") == 0 && parts == 3)
        {
            int x = atoi(a);
            int y = atoi(b);
            gs_handle_move(sock, x, y);
            continue;
        }
        // FORFEIT: for auto-forfeit. SURRENDER: for surrender
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

        else
        {
            send_all(sock, "ERROR|Unknown command\n", 23);
        }
    }

    printf("[Server] Client disconnected: %d\n", sock);
    close(sock);
    return NULL;
}

static void *afk_watcher(void *arg)
{
    while (1) {
        sleep(1);
        gs_tick_afk();
    }
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


    printf("[AFK] Auto-forfeit watcher started (30s)...\n");

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


