# Prereqs:
#   apt install musl-tools

all: testinit

testinit: testinit.c
	musl-gcc -o $@ -Wall -Werror -static $^

clean:
	rm testinit

.PHONY: all clean
