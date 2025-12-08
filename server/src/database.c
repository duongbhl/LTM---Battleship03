#include "../include/database.h"
#include <stdio.h>
#include <string.h>

sqlite3* g_db = NULL;

int db_init(const char* filename)
{
    if (sqlite3_open(filename, &g_db) != SQLITE_OK) {
        fprintf(stderr, "DB OPEN ERROR: %s\n", sqlite3_errmsg(g_db));
        return -1;
    }

    const char* sql =
        "CREATE TABLE IF NOT EXISTS users ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " username TEXT UNIQUE,"
        " password TEXT,"
        " elo INTEGER DEFAULT 1000"
        ");";

    char* err = NULL;
    if (sqlite3_exec(g_db, sql, NULL, NULL, &err) != SQLITE_OK) {
        fprintf(stderr, "DB CREATE TABLE ERROR: %s\n", err);
        sqlite3_free(err);
        return -1;
    }

    return 0;
}

void db_close(void)
{
    if (g_db) {
        sqlite3_close(g_db);
        g_db = NULL;
    }
}

int db_register_user(const char* user, const char* pass,
                     char* errbuf, size_t errsz)
{
    const char* sql =
        "INSERT INTO users(username, password) VALUES(?, ?)";

    sqlite3_stmt* st = NULL;

    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) {
        snprintf(errbuf, errsz, "DB_ERROR");
        return -1;
    }

    sqlite3_bind_text(st, 1, user, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, pass, -1, SQLITE_STATIC);

    int rc = sqlite3_step(st);
    sqlite3_finalize(st);

    if (rc != SQLITE_DONE) {
        snprintf(errbuf, errsz, "USERNAME_EXISTS");
        return -1;
    }

    return 0;
}

int db_login_user(const char* user, const char* pass,
                  int* out_elo,
                  char* errbuf, size_t errsz)
{
    const char* sql =
        "SELECT password, elo FROM users WHERE username=?";

    sqlite3_stmt* st = NULL;

    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK) {
        snprintf(errbuf, errsz, "DB_ERROR");
        return -1;
    }

    sqlite3_bind_text(st, 1, user, -1, SQLITE_STATIC);

    int rc = sqlite3_step(st);

    if (rc == SQLITE_ROW) {
        const char* db_pass = (const char*)sqlite3_column_text(st, 0);
        int elo = sqlite3_column_int(st, 1);

        if (strcmp(db_pass, pass) == 0) {
            if (out_elo) *out_elo = elo;
            sqlite3_finalize(st);
            return 0;
        } else {
            snprintf(errbuf, errsz, "WRONG_PASSWORD");
            sqlite3_finalize(st);
            return -1;
        }
    }

    snprintf(errbuf, errsz, "USER_NOT_FOUND");
    sqlite3_finalize(st);
    return -1;
}

int db_get_elo(const char *username)
{
    sqlite3_stmt *stmt;
    const char *sql = "SELECT elo FROM users WHERE username=?;";

    if (sqlite3_prepare_v2(g_db, sql, -1, &stmt, NULL) != SQLITE_OK)
        return 1000; // elo mặc định

    sqlite3_bind_text(stmt, 1, username, -1, SQLITE_STATIC);

    int elo = 1000;

    if (sqlite3_step(stmt) == SQLITE_ROW) {
        elo = sqlite3_column_int(stmt, 0);
    }

    sqlite3_finalize(stmt);
    return elo;
}
