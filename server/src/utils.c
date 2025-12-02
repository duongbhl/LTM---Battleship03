#include "../include/utils.h"
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>

size_t send_all(int sock, const char* data, size_t len)
{
    size_t sent = 0;
    while (sent < len) {
        ssize_t n = send(sock, data + sent, len - sent, 0);
        if (n <= 0) return n;
        sent += (size_t)n;
    }
    return (ssize_t)sent;
}

void trim_newline(char* s)
{
    if (!s) return;
    size_t len = strlen(s);
    while (len > 0 && (s[len-1] == '\n' || s[len-1] == '\r')) {
        s[len-1] = '\0';
        len--;
    }
}
