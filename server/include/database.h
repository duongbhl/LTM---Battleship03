#ifndef DATABASE_H
#define DATABASE_H

#include <sqlite3.h>


void db_init();
void db_close();

extern sqlite3* db;

#endif
