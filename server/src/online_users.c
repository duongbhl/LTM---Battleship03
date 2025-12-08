#include "online_users.h"
#include <string.h>

typedef struct {
    char username[32];
    int sock;
} OnlineUser;

static OnlineUser list[200];
static int count = 0;

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
            return;
        }
    }
    strncpy(list[count].username, user, 31);
    list[count].sock = sock;
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
