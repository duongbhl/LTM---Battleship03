#include "../include/database.h"
#include <stdio.h>
#include <string.h>
#include <time.h>

sqlite3 *g_db = NULL;

int db_init(const char *filename)
{
    if (sqlite3_open(filename, &g_db) != SQLITE_OK)
    {
        fprintf(stderr, "DB OPEN ERROR: %s\n", sqlite3_errmsg(g_db));
        return -1;
    }

    const char *sql_users =
        "CREATE TABLE IF NOT EXISTS users ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " username TEXT UNIQUE,"
        " password TEXT,"
        " elo INTEGER DEFAULT 1000"
        ");";

    const char *sql_matches =
        "CREATE TABLE IF NOT EXISTS matches ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " user TEXT NOT NULL,"
        " opponent TEXT NOT NULL,"
        " result TEXT NOT NULL,"
        " elo_change INTEGER NOT NULL,"
        " created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
        ");";

    /* ✅ NEW: FRIENDS TABLE */
    const char *sql_friends =
        "CREATE TABLE IF NOT EXISTS friends ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " user TEXT NOT NULL,"
        " friend TEXT NOT NULL,"
        " status TEXT NOT NULL,"
        " created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
        " UNIQUE(user, friend)"
        ");";

    char *err = NULL;

    if (sqlite3_exec(g_db, sql_users, NULL, NULL, &err) != SQLITE_OK)
    {
        fprintf(stderr, "DB CREATE USERS TABLE ERROR: %s\n", err);
        sqlite3_free(err);
        return -1;
    }

    if (sqlite3_exec(g_db, sql_matches, NULL, NULL, &err) != SQLITE_OK)
    {
        fprintf(stderr, "DB CREATE MATCHES TABLE ERROR: %s\n", err);
        sqlite3_free(err);
        return -1;
    }

    /* ✅ CREATE FRIENDS TABLE */
    if (sqlite3_exec(g_db, sql_friends, NULL, NULL, &err) != SQLITE_OK)
    {
        fprintf(stderr, "DB CREATE FRIENDS TABLE ERROR: %s\n", err);
        sqlite3_free(err);
        return -1;
    }

    return 0;
}

void db_close(void)
{
    if (g_db)
    {
        sqlite3_close(g_db);
        g_db = NULL;
    }
}

int db_register_user(const char *user, const char *pass, char *errbuf, size_t errsz)
{
    const char *sql =
        "INSERT INTO users(username, password) VALUES(?, ?)";

    sqlite3_stmt *st = NULL;

    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK)
    {
        snprintf(errbuf, errsz, "DB_ERROR");
        return -1;
    }

    sqlite3_bind_text(st, 1, user, -1, SQLITE_STATIC);
    sqlite3_bind_text(st, 2, pass, -1, SQLITE_STATIC);

    int rc = sqlite3_step(st);
    sqlite3_finalize(st);

    if (rc != SQLITE_DONE)
    {
        snprintf(errbuf, errsz, "USERNAME_EXISTS");
        return -1;
    }

    return 0;
}

int db_login_user(const char *user, const char *pass, int *out_elo, char *errbuf, size_t errsz)
{
    const char *sql =
        "SELECT password, elo FROM users WHERE username=?";

    sqlite3_stmt *st = NULL;

    if (sqlite3_prepare_v2(g_db, sql, -1, &st, NULL) != SQLITE_OK)
    {
        snprintf(errbuf, errsz, "DB_ERROR");
        return -1;
    }

    sqlite3_bind_text(st, 1, user, -1, SQLITE_STATIC);

    int rc = sqlite3_step(st);

    if (rc == SQLITE_ROW)
    {
        const char *db_pass = (const char *)sqlite3_column_text(st, 0);
        int elo = sqlite3_column_int(st, 1);

        if (strcmp(db_pass, pass) == 0)
        {
            if (out_elo)
                *out_elo = elo;
            sqlite3_finalize(st);
            return 0;
        }
        else
        {
            snprintf(errbuf, errsz, "WRONG_PASSWORD");
            sqlite3_finalize(st);
            return -1;
        }
    }

    snprintf(errbuf, errsz, "USER_NOT_FOUND");
    sqlite3_finalize(st);
    return -1;
}

int db_user_exists(const char *username) {
    sqlite3_stmt *stmt;
    const char *sql = "SELECT 1 FROM users WHERE username = ? LIMIT 1";

    if (sqlite3_prepare_v2(g_db, sql, -1, &stmt, NULL) != SQLITE_OK) {
        return 0;
    }

    sqlite3_bind_text(stmt, 1, username, -1, SQLITE_STATIC);

    int exists = (sqlite3_step(stmt) == SQLITE_ROW);

    sqlite3_finalize(stmt);
    return exists;
}


int db_get_elo(const char *username)
{
    sqlite3_stmt *stmt;
    const char *sql = "SELECT elo FROM users WHERE username=?;";

    if (sqlite3_prepare_v2(g_db, sql, -1, &stmt, NULL) != SQLITE_OK)
        return 1000; // elo mặc định

    sqlite3_bind_text(stmt, 1, username, -1, SQLITE_STATIC);

    int elo = 1000;

    if (sqlite3_step(stmt) == SQLITE_ROW)
    {
        elo = sqlite3_column_int(stmt, 0);
    }

    sqlite3_finalize(stmt);
    return elo;
}

void db_set_elo(const char *username, int elo)
{
    if (!g_db || !username)
        return;

    const char *sql =
        "UPDATE users SET elo = ? WHERE username = ?;";

    sqlite3_stmt *stmt = NULL;

    int rc = sqlite3_prepare_v2(g_db, sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK)
    {
        fprintf(stderr,
                "[DB] db_set_elo prepare failed: %s\n",
                sqlite3_errmsg(g_db));
        return;
    }

    sqlite3_bind_int(stmt, 1, elo);
    sqlite3_bind_text(stmt, 2, username, -1, SQLITE_TRANSIENT);

    rc = sqlite3_step(stmt);
    if (rc != SQLITE_DONE)
    {
        fprintf(stderr,
                "[DB] db_set_elo step failed: %s\n",
                sqlite3_errmsg(g_db));
    }
    else if (sqlite3_changes(g_db) == 0)
    {
        fprintf(stderr,
                "[DB] db_set_elo warning: user '%s' not found\n",
                username);
    }

    sqlite3_finalize(stmt);
}

void db_add_history(const char *user,
                    const char *opponent,
                    const char *result,
                    int elo_change)
{
    if (!g_db)
        return;

    const char *sql =
        "INSERT INTO matches (user, opponent, result, elo_change)"
        " VALUES (?, ?, ?, ?);";

    sqlite3_stmt *stmt;

    if (sqlite3_prepare_v2(g_db, sql, -1, &stmt, NULL) != SQLITE_OK)
        return;

    sqlite3_bind_text(stmt, 1, user, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 2, opponent, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 3, result, -1, SQLITE_TRANSIENT);
    sqlite3_bind_int(stmt, 4, elo_change);

    sqlite3_step(stmt);
    sqlite3_finalize(stmt);
}

void db_get_history(const char *user, int sock)
{
    const char *sql =
        "SELECT created_at, result, opponent, elo_change "
        "FROM matches "
        "WHERE user = ? "
        "ORDER BY created_at DESC "
        "LIMIT 20;";

    sqlite3_stmt *stmt;

    if (sqlite3_prepare_v2(g_db, sql, -1, &stmt, NULL) != SQLITE_OK)
        return;

    sqlite3_bind_text(stmt, 1, user, -1, SQLITE_TRANSIENT);

    while (sqlite3_step(stmt) == SQLITE_ROW)
    {
        const char *date = (const char *)sqlite3_column_text(stmt, 0);
        const char *result = (const char *)sqlite3_column_text(stmt, 1);
        const char *opp = (const char *)sqlite3_column_text(stmt, 2);
        int elo = sqlite3_column_int(stmt, 3);

        char buf[256];
        snprintf(buf, sizeof(buf),
                 "HISTORY|%s|%s|%s|%+d\n",
                 date, result, opp, elo);

        send_logged(sock, buf);
    }

    sqlite3_finalize(stmt);
}

int db_friend_request_exists(const char *from, const char *to)
{
    sqlite3_stmt *stmt;
    const char *sql =
        "SELECT 1 FROM friends WHERE user=? AND friend=? LIMIT 1";

    sqlite3_prepare_v2(g_db, sql, -1, &stmt, NULL);
    sqlite3_bind_text(stmt, 1, from, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, to, -1, SQLITE_STATIC);

    int exists = (sqlite3_step(stmt) == SQLITE_ROW);
    sqlite3_finalize(stmt);
    return exists;
}

void db_insert_friend_request(const char *from, const char *to)
{
    sqlite3_stmt *stmt;
    const char *sql =
        "INSERT OR REPLACE INTO friends (user, friend, status) "
        "VALUES (?, ?, 'pending')";

    if (sqlite3_prepare_v2(g_db, sql, -1, &stmt, NULL) != SQLITE_OK)
        return;

    sqlite3_bind_text(stmt, 1, from, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, to, -1, SQLITE_STATIC);

    sqlite3_step(stmt);
    sqlite3_finalize(stmt);
}


void db_accept_friend(const char *from, const char *to)
{
    sqlite3_stmt *stmt;

    // Update request to ACCEPTED
    const char *sql1 =
        "UPDATE friends SET status='ACCEPTED' "
        "WHERE user=? AND friend=?";

    sqlite3_prepare_v2(g_db, sql1, -1, &stmt, NULL);
    sqlite3_bind_text(stmt, 1, from, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, to, -1, SQLITE_STATIC);
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    // Insert reverse row
    const char *sql2 =
        "INSERT OR IGNORE INTO friends(user, friend, status) "
        "VALUES(?, ?, 'ACCEPTED')";

    sqlite3_prepare_v2(g_db, sql2, -1, &stmt, NULL);
    sqlite3_bind_text(stmt, 1, to, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, from, -1, SQLITE_STATIC);
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);
}

void db_delete_friend(const char *user, const char *friend)
{
    sqlite3_stmt *stmt;
    const char *sql =
        "DELETE FROM friends WHERE user=? AND friend=?";

    sqlite3_prepare_v2(g_db, sql, -1, &stmt, NULL);
    sqlite3_bind_text(stmt, 1, user, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, friend, -1, SQLITE_STATIC);
    sqlite3_step(stmt);
    sqlite3_finalize(stmt);
}

int db_get_accepted_friends(const char *user, char out[][32], int max)
{
    sqlite3_stmt *stmt;
    const char *sql =
        "SELECT friend AS name FROM friends "
        "WHERE user=? AND status='ACCEPTED' "
        "UNION "
        "SELECT user AS name FROM friends "
        "WHERE friend=? AND status='ACCEPTED'";

    if (sqlite3_prepare_v2(g_db, sql, -1, &stmt, NULL) != SQLITE_OK)
        return 0;

    sqlite3_bind_text(stmt, 1, user, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, user, -1, SQLITE_STATIC);

    int count = 0;
    while (sqlite3_step(stmt) == SQLITE_ROW && count < max)
    {
        const char *name = (const char *)sqlite3_column_text(stmt, 0);
        if (name) {
            strncpy(out[count], name, 31);
            out[count][31] = '\0';
            count++;
        }
    }

    sqlite3_finalize(stmt);
    return count;
}


int db_get_pending_invites(const char *to_user, char out[][32], int max)
{
    sqlite3_stmt *stmt;
    const char *sql =
        "SELECT user FROM friends WHERE friend=? AND status='pending'";

    if (sqlite3_prepare_v2(g_db, sql, -1, &stmt, NULL) != SQLITE_OK) {
        return 0;
    }
    sqlite3_bind_text(stmt, 1, to_user, -1, SQLITE_STATIC);

    int n = 0;
    while (sqlite3_step(stmt) == SQLITE_ROW && n < max) {
        const unsigned char *u = sqlite3_column_text(stmt, 0);
        if (u) {
            strncpy(out[n], (const char*)u, 31);
            out[n][31] = '\0';
            n++;
        }
    }
    sqlite3_finalize(stmt);
    return n;
}

