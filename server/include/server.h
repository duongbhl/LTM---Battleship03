#ifndef SERVER_H
#define SERVER_H

void server_init(int port);
void server_run();
void send_response(int sock, const char* status, const char* message);


#endif // SERVER_H