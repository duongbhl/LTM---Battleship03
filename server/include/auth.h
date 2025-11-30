#ifndef AUTH_H
#define AUTH_H

void handle_login(int sock, const char *data);
void handle_register(int sock, const char *data);

#endif
