#include <stdio.h>
#include <unistd.h>
#include "../include/game_session.h"

void *afk_watcher(void *arg)
{
    while (1) {
        gs_tick_afk();    
        sleep(1);
    }
    return NULL;
}