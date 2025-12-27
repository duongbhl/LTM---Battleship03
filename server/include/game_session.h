#ifndef GAME_SESSION_H
#define GAME_SESSION_H

void gs_create_session(int sock1, const char* user1, int elo1,
                       int sock2, const char* user2, int elo2);

void gs_handle_move(int sock, int x, int y);
int gs_get_opponent_sock(int sock);
void gs_send_react(int from_sock, const char *emoji);


#endif
