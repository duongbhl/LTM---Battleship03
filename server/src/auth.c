#include "../include/auth.h"
#include "../include/database.h"
#include "../include/utils.h"

#include <stdio.h>
#include <string.h>

void handle_login(int sock, const char *user, const char *pass)
{
    int elo = 0;
    char err[128];

    if (db_login_user(user, pass, &elo, err, sizeof(err)) == 0) {
        // LOGIN_OK|message
        char msg[128];
        snprintf(msg, sizeof(msg), "LOGIN_OK|%d", elo);
        send_all(sock, msg, strlen(msg));
    } else {
        // LOGIN_FAIL|reason
        char msg[256];
        snprintf(msg, sizeof(msg), "LOGIN_FAIL|%s", err);
        send_all(sock, msg, strlen(msg));
    }
}

void handle_register(int sock, const char *user, const char *pass)
{
    char err[128];

    if (db_register_user(user, pass, err, sizeof(err)) == 0) {
        // REGISTER_SUCCESS|message  ✅ để client lấy message hiển thị
        const char *msg = "REGISTER_SUCCESS|";
        send_all(sock, msg, strlen(msg));
    } else {
        // REGISTER_FAIL|reason
        char msg[256];
        snprintf(msg, sizeof(msg), "REGISTER_FAIL|", err);
        send_all(sock, msg, strlen(msg));
    }
}
