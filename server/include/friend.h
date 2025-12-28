#ifndef FRIEND_H
#define FRIEND_H

void handle_friend_request(int sock, const char *from, const char *to);
void handle_friend_accept(int sock, const char *me, const char *other);
void handle_friend_reject(int sock, const char *me, const char *other);

void handle_get_friends_online(int sock, const char *user);

/* Direct challenge (ELO / ranked match) between online friends */
void handle_challenge_elo(int sock, const char *from, const char *to);
void handle_challenge_accept(int sock, const char *me, const char *other);
void handle_challenge_decline(int sock, const char *me, const char *other);
void handle_challenge_cancel(int sock, const char *from, const char *to);

#endif
