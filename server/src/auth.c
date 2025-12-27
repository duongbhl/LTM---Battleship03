#include "../include/auth.h"
#include "../include/database.h"
#include "../include/utils.h"
#include "../include/online_users.h"

#include <stdio.h>
#include <string.h>

void handle_login(int sock, const char *user, const char *pass)
{
    int elo = 0;
    char err[128];

    // ---- CHECK nếu tài khoản đã login ----
    if (user_is_online(user)) {
        char msg[128];
        snprintf(msg, sizeof(msg), "LOGIN_FAIL|Account already logged in\n");
        send_logged(sock, msg);
        return;
    }

    // ---- CHECK username/password ----
    if (db_login_user(user, pass, &elo, err, sizeof(err)) == 0)
    {
        // ---- Đánh dấu ONLINE ----
        user_set_online(user, sock);

        char msg[128];
        snprintf(msg, sizeof(msg), "LOGIN_OK|%d\n", elo);
        send_logged(sock, msg);
    }
    else
    {
        char msg[256];
        snprintf(msg, sizeof(msg), "LOGIN_FAIL|%s\n", err);
        send_logged(sock, msg);
    }
}

void handle_register(int sock, const char *user, const char *pass)
{
    char err[128];

    if (db_register_user(user, pass, err, sizeof(err)) == 0)
    {
        send_logged(sock, "REGISTER_SUCCESS|\n");
    }
    else
    {
        char msg[256];
        snprintf(msg, sizeof(msg), "REGISTER_FAIL|%s\n", err);
        send_logged(sock, msg);
    }
}