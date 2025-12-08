#ifndef ONLINE_USERS_H
#define ONLINE_USERS_H

int user_is_online(const char *user);
void user_set_online(const char *user, int sock);
void user_set_offline_by_sock(int sock);
const char *user_of_sock(int sock);

#endif
