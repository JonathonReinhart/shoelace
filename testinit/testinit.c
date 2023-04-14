#include <stdio.h>
#include <unistd.h>
#include <dirent.h>
#include <sys/reboot.h>


static void showdir(const char *path)
{
    struct dirent *ent;
    DIR *dir;

    dir = opendir(path);
    if (!dir) {
        fprintf(stderr, "Failed to open %s\n", path);
        return;
    }

    printf("Contents of %s:\n", path);

    while ((ent = readdir(dir))) {
        printf("%s%s\n",
            ent->d_name,
            ent->d_type == DT_DIR ? "/" : ""
            );
    }

    closedir(dir);
}

int main(int argc, char *argv[])
{
    int rc;

    printf("HELLO WORLD!\n");

    printf("argv:\n");
    for (int i = 0; i < argc; ++i) {
        printf("[%d] = \"%s\"\n", i, argv[i]);
    }

    showdir("/");
    printf("\n");
    showdir("/bin");

    sync();
    rc = reboot(RB_POWER_OFF);
    if (rc) {
        printf("reboot() returned %d\n", rc);
    }

    pause();

    return 0; 
}
