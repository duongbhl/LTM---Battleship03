#include "utils.h"
#include <string.h>

void trim_newline(char* s) {
    s[strcspn(s, "\r\n")] = 0;
}
