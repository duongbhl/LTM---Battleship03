#include "server.h"
#include "database.h"
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

            // ------------------ ADD START ------------------
            char buffer[256] = {0};
            int bytes = recv(client, buffer, sizeof(buffer)-1, 0);

            if (bytes > 0) {
                printf("Received: %s\n", buffer);

                char cmd[32], user[64], pass[64];
                sscanf(buffer, "%31[^|]|%63[^|]|%63[^|]", cmd, user, pass);

                if (strcmp(cmd, "LOGIN") == 0) {

                    printf("Checking login for %s...\n", user);

                    if (db_login(user, pass)) {
                        send_response(client, "LOGIN_OK", "Welcome");
                    } else {
                        send_response(client, "LOGIN_FAIL", "Invalid username or password");
                    }
                }
                else if (strcmp(cmd, "REGISTER") == 0) {

                    if (db_register(user, pass)) {
                        send_response(client, "REGISTER_SUCCESS", "Account created");
                    } else {
                        send_response(client, "REGISTER_FAIL", "Username already exists");
                    }
                }
                else {
                    send_response(client, "ERROR", "Invalid command");
                }
            }
            // ------------------ ADD END ------------------
            close(client);
        }
    }
}


void send_response(int sock, const char* status, const char* message) {
    char buffer[256];
    snprintf(buffer, sizeof(buffer), "%s|%s\n", status, message);
    printf("Sending response: %s\n", buffer);
    send(sock, buffer, strlen(buffer), 0);
}