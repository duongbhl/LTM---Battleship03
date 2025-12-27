#ifndef DATABASE_H
#define DATABASE_H

#include <stddef.h>
#include <sqlite3.h>

extern sqlite3* g_db;

int db_init(const char* filename);
void db_close(void);

int db_register_user(const char* user, const char* pass,
                     char* errbuf, size_t errsz);

int db_login_user(const char* user, const char* pass,
                  int* out_elo,
                  char* errbuf, size_t errsz);
                  
int db_get_elo(const char *username);

void db_set_elo(const char *username, int elo);


void db_add_history(
    const char *user,
    const char *opponent,
    const char *result,
    int elo_change
);

void db_get_history(const char *user, int sock);



#endif
