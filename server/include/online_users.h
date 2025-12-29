#ifndef ONLINE_USERS_H
#define ONLINE_USERS_H
#include <time.h>

typedef enum {
    STATE_IDLE,
    STATE_QUEUE,
    STATE_IN_GAME
} ClientState;


typedef struct {
    char username[32];
    int sock;
    int logged_in;
    ClientState state;
    time_t last_ping;

} OnlineUser;

static OnlineUser list[200];
static int count = 0;

int user_is_online(const char *user);
void user_set_online(const char *user, int sock);
void user_set_offline_by_sock(int sock);
const char *user_of_sock(int sock);
int user_online_count(void);
void user_get_all(char *out, int maxlen);
int user_get_sock(const char *username);
void online_users_tick(void);
void online_user_update_ping(int sock);
OnlineUser *online_user_by_sock(int sock);


#endif
