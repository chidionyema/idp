/* A disposable listener for the api-port-guard falsifier: the only thing a guard bug can kill. */
#include <arpa/inet.h>
#include <netinet/in.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <unistd.h>
int main(int argc, char **argv) {
    int s = socket(AF_INET, SOCK_STREAM, 0), one = 1;
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET; a.sin_port = htons(argc > 1 ? atoi(argv[1]) : 0);
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    if (bind(s, (struct sockaddr *)&a, sizeof a) || listen(s, 16)) return 1;
    for (;;) {  /* accept and drop, so a liveness probe never fills the backlog */
        int c = accept(s, 0, 0);
        if (c >= 0) close(c);
    }
}
