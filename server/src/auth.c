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
        push_pending_invites(sock, user);
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


void handle_logout(int sock, const char *user)
{
    if (user && user[0] != '\0') {
        user_set_offline_by_sock(sock);
        printf("[LOGOUT] %s logged out\n", user);
    }

    send_logged(sock, "LOGOUT_OK|\n");
    close(sock);
}


void push_pending_invites(int sock, const char *user)
{
    char senders[64][32];
    int n = db_get_pending_invites(user, senders, 64);

    char buf[2048];
    buf[0] = '\0';

    for (int i = 0; i < n; i++) {
        strcat(buf, senders[i]);
        if (i < n - 1) strcat(buf, ",");
    }

    char msg[2100];
    snprintf(msg, sizeof(msg), "FRIEND_INVITES|%s\n", buf);
    send_logged(sock, msg);
}

