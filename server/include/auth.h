#ifndef AUTH_H
#define AUTH_H

void handle_client(int client_sock);
void handle_login(int sock, const char *u, const char *p);
void handle_register(int sock, const char *u, const char *p);
#endif
