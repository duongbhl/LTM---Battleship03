#ifndef DATABASE_H
#define DATABASE_H

#include <stddef.h>
#include <sqlite3.h>

extern sqlite3* g_db;

int db_init(const char* filename);
void db_close(void);


// USER MANAGEMENT
int db_register_user(const char* user, const char* pass,char* errbuf, size_t errsz);

int db_login_user(const char* user, const char* pass,int* out_elo,char* errbuf, size_t errsz);

// ELO MANAGEMENT
int db_get_elo(const char *username);

void db_set_elo(const char *username, int elo);


// MATCH HISTORY
void db_add_history(const char *user,const char *opponent,const char *result,int elo_change);

void db_get_history(const char *user, int sock);

// FRIEND SYSTEM
int db_friend_request_exists(const char *from, const char *to);

void db_insert_friend_request(const char *from, const char *to);

void db_accept_friend(const char *from, const char *to);

void db_delete_friend(const char *user, const char *friend);

int db_get_accepted_friends(const char *user, char out[][32], int max);


#endif
