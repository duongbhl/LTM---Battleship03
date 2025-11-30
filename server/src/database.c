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

int db_register(const char* user, const char* pass) {
    sqlite3_stmt* stmt;
    const char* sql = "INSERT INTO users(username, password) VALUES(?, ?)";
    
    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK)
        return 0;

    sqlite3_bind_text(stmt, 1, user, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, pass, -1, SQLITE_STATIC);

    if (sqlite3_step(stmt) != SQLITE_DONE) {
        sqlite3_finalize(stmt);
        return 0;   // insert fail (username exists)
    }

    sqlite3_finalize(stmt);
    return 1;       // success
}


int db_login(const char* user, const char* pass) {
    sqlite3_stmt* stmt;
    const char* sql = "SELECT id FROM users WHERE username=? AND password=?";

    if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK)
        return 0;

    sqlite3_bind_text(stmt, 1, user, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, pass, -1, SQLITE_STATIC);

    int ret = 0;
    if (sqlite3_step(stmt) == SQLITE_ROW)
        ret = 1; // match

    sqlite3_finalize(stmt);
    return ret;
}


