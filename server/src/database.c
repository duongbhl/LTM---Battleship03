#include "database.h"
#include <stdio.h>
#include <string.h>
#include <unistd.h>

sqlite3* db = NULL;

void db_init() {
    if (sqlite3_open("battleship.db", &db) != SQLITE_OK) {
        printf("Cannot open database!\n");
        exit(1);
    }
    printf("Database connected!\n");
}

void db_close() {
    if (db) sqlite3_close(db);
}

