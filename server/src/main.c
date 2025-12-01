#include "../include/database.h"
#include "../include/server.h"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

int main(void)
{
    srand((unsigned int)time(NULL));

    if (db_init("battleship.db") != 0) {
        fprintf(stderr, "Failed to init database.\n");
        return 1;
    }
    server_init(5050);
    server_run();

    db_close();
    return 0;
}
