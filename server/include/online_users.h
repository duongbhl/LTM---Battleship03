#ifndef ONLINE_USERS_H
#define ONLINE_USERS_H

int user_is_online(const char *user);
void user_set_online(const char *user, int sock);
void user_set_offline_by_sock(int sock);
const char *user_of_sock(int sock);
int user_online_count(void);
void user_get_all(char *out, int maxlen);
int user_get_sock(const char *username);


#endif
