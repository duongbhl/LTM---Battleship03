#pragma once
#ifndef MATCHMAKING_H
#define MATCHMAKING_H

void mm_request_match(int sock, const char* user, int elo, int use_elo);

void mm_start_worker(void);
void mm_stop_worker(void);

#endif
