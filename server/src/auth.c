#include "../include/auth.h"
#include "../include/database.h"
#include <stdio.h>
#include <string.h>

void handle_register(int sock, const char *data) {
    char user[64], pass[64];
    sscanf(data, "%63[^|]|%63s", user, pass);

    if (db_register(user, pass))
        send_response(sock, "ok", "Register successful");
    else
        send_response(sock, "error", "Username already exists");
}

void handle_login(int sock, const char *data) {
    char user[64], pass[64];
    sscanf(data, "%63[^|]|%63s", user, pass);

    if (db_login(user, pass))
        send_response(sock, "ok", "Login successful");
    else
        send_response(sock, "error", "Invalid username or password");
}
