#include "server.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>

int listen_sock;

void server_init(int port) {
    listen_sock = socket(AF_INET, SOCK_STREAM, 0);

    if (listen_sock < 0) {
        perror("socket");
        exit(1);
    }

    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(port);

    if (bind(listen_sock, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        perror("bind");
        exit(1);
    }

    if (listen(listen_sock, 5) < 0) {
        perror("listen");
        exit(1);
    }

    printf("SERVER STARTED ON PORT %d\n", port);
}

void server_run() {
    while (1) {
        int client = accept(listen_sock, NULL, NULL);
        if (client >= 0) {
            printf("New client connected!\n");
            close(client);
        }
    }
}
