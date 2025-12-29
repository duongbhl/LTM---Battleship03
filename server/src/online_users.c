#include "../include/online_users.h"
#include "../include/game_session.h"
#include <string.h>
#include <time.h>



int user_is_online(const char *user)
{
    for (int i = 0; i < count; i++)
        if (strcmp(list[i].username, user) == 0)
            return 1;
    return 0;
}

void user_set_online(const char *user, int sock)
{
    for (int i = 0; i < count; i++) {
        if (strcmp(list[i].username, user) == 0) {
            list[i].sock = sock;
            list[i].logged_in = 1;
            list[i].state = STATE_IDLE;
            list[i].last_ping = time(NULL);
            return;
        }
    }
    strncpy(list[count].username, user, 31);
    list[count].sock = sock;
    list[count].logged_in = 1;
    list[count].state = STATE_IDLE;
    list[count].last_ping = time(NULL);
    count++;
}

void user_set_offline_by_sock(int sock)
{
    for (int i = 0; i < count; i++) {
        if (list[i].sock == sock) {
            list[i] = list[count - 1];
            count--;
            return;
        }
    }
}

const char *user_of_sock(int sock)
{
    for (int i = 0; i < count; i++)
        if (list[i].sock == sock)
            return list[i].username;

    return NULL;
}

int user_online_count(void)
{
    return count;
}

void user_get_all(char *out, int maxlen)
{
    out[0] = '\0';
    for (int i = 0; i < count; i++) {
        strncat(out, list[i].username, maxlen - strlen(out) - 1);
        if (i != count - 1)
            strncat(out, ",", maxlen - strlen(out) - 1);
    }
}

int user_get_sock(const char *username)
{
    for (int i = 0; i < count; i++)
    {
        if (strcmp(list[i].username, username) == 0)
            return list[i].sock;
    }
    return -1;
}

void online_users_tick(void)
{
    time_t now = time(NULL);

    for (int i = 0; i < count; i++)
    {
        OnlineUser *u = &list[i];

        if (u->sock <= 0) continue;

        if (now - u->last_ping > 15)
        {
            printf("[PING] timeout sock=%d\n", u->sock);
            gs_handle_disconnect(u->sock);
        }
    }
}

void online_user_update_ping(int sock)
{
    OnlineUser *u = online_user_by_sock(sock);
    if (u)
        u->last_ping = time(NULL);
}

OnlineUser *online_user_by_sock(int sock)
{
    for (int i = 0; i < count; i++)
    {
        if (list[i].sock == sock)
            return &list[i];
    }
    return NULL;
}
