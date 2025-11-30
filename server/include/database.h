#ifndef DATABASE_H
#define DATABASE_H

#include <sqlite3.h>


void db_init();
void db_close();

int db_register(const char* user, const char* pass);
int db_login(const char* user, const char* pass);

extern sqlite3* db;

#endif
