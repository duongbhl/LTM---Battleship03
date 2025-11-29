#include "server.h"
#include "database.h"

int main() {
    db_init();                 //ket noi db
    server_init(5050);         // tạo socket, bind, listen
    server_run();              // vòng accept()
    return 0;
}
