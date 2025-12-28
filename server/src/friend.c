#include "../include/friend.h"
#include "../include/database.h"
#include "../include/online_users.h"
#include "../include/utils.h"
#include <string.h>
#include <stdio.h>

// void handle_friend_request(int sock, const char *from, const char *to)
// {
//     // chỉ check user tồn tại
//     if (!db_user_exists(to))
//     {
//         send_logged(sock, "ERROR|User does not exist\n");
//         return;
//     }

//     db_insert_friend_request(from, to);

//     int to_sock = user_get_sock(to);
//     // if (to_sock >= 0)
//     // {
//     //     char msg[128];
//     //     snprintf(msg, sizeof(msg), "FRIEND_INVITE|%s\n", from);
//     //     send_logged(to_sock, msg);
//     // }

//     char msg[128];
//     snprintf(msg, sizeof(msg), "FRIEND_INVITE|%s\n", from);
//     send_logged(1, msg);
// }


void handle_friend_request(int sock, const char *from, const char *to)
{
    if (!db_user_exists(to)) {
        send_logged(sock, "ERROR|User does not exist\n");
        return;
    }

    // luôn lưu (online/offline đều lưu)
    db_insert_friend_request(from, to);

    // báo lại cho người gửi để UI hiện "đã gửi"
    {
        char ok[128];
        snprintf(ok, sizeof(ok), "FRIEND_SENT|%s\n", to);
        send_logged(sock, ok);
    }

    // nếu người nhận đang online thì push realtime
    int to_sock = user_get_sock(to);
    if (to_sock >= 0) {
        char msg[128];
        snprintf(msg, sizeof(msg), "FRIEND_INVITE|%s\n", from);
        send_logged(to_sock, msg);
    }
}


void handle_friend_accept(int sock, const char *me, const char *other)
{
    if (!db_friend_request_exists(other, me))
    {
        send_logged(sock, "ERROR|No friend request\n");
        return;
    }

    db_accept_friend(other, me);

    send_logged(sock, "FRIEND_ACCEPTED\n");

    int other_sock = user_get_sock(other);
    if (other_sock >= 0)
    {
        char msg[64];
        snprintf(msg, sizeof(msg), "FRIEND_ACCEPTED|%s\n", me);
        send_logged(other_sock, msg);
    }
}

void handle_friend_reject(int sock, const char *me, const char *other)
{
    db_delete_friend(me, other);
    send_logged(sock, "FRIEND_REJECTED\n");
}

void handle_get_friends_online(int sock, const char *user)
{
    char friends[64][32];
    int n = db_get_accepted_friends(user, friends, 64);

    char out[1024] = "";
    for (int i = 0; i < n; i++)
    {
        if (user_is_online(friends[i]))
        {
            strcat(out, friends[i]);
            strcat(out, ",");
        }
    }

    char msg[1100];
    snprintf(msg, sizeof(msg), "FRIENDS_ONLINE|%s\n", out);
    send_logged(sock, msg);
}
