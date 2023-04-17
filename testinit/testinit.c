/*
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

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
