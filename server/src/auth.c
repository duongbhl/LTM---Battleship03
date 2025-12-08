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

    if (user_is_online(user)) {
        char msg[128];
        snprintf(msg, sizeof(msg), "LOGIN_FAIL|Account already logged in\n");
        send_all(sock, msg, strlen(msg));
        return;
    }

    if (db_login_user(user, pass, &elo, err, sizeof(err)) == 0)
    {
        // Mark online
        user_set_online(user, sock);

        // LOGIN_OK|message
        char msg[128];
        snprintf(msg, sizeof(msg), "LOGIN_OK|%d\n", elo);
        send_all(sock, msg, strlen(msg));
    }
    else
    {
        // LOGIN_FAIL|reason
        char msg[256];
        snprintf(msg, sizeof(msg), "LOGIN_FAIL|%s\n", err);
        send_all(sock, msg, strlen(msg));
    }
}

void handle_register(int sock, const char *user, const char *pass)
{
    char err[128];

    if (db_register_user(user, pass, err, sizeof(err)) == 0)
    {
        // REGISTER_SUCCESS|message  
        const char *msg = "REGISTER_SUCCESS|";
        send_all(sock, msg, strlen(msg));
    }
    else
    {
        // REGISTER_FAIL|reason
        char msg[256];
        snprintf(msg, sizeof(msg), "REGISTER_FAIL|%s\n", err);
        send_all(sock, msg, strlen(msg));
    }
}
