#ifndef UTILS_H
#define UTILS_H

#include <stddef.h>

size_t send_all(int sock, const char* data, size_t len);
void trim_newline(char* s);

#endif
