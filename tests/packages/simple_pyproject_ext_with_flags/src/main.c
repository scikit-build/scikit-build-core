#include <assert.h>
#include <stdbool.h>
#include <stdio.h>

#ifndef FOO
static_assert(false, "FOO must be defined");
#elif FOO != 1
static_assert(false, "FOO must be 1");
#endif
#ifndef BAR
static_assert(false, "BAR must be defined");
#endif

int main() {
    printf("Hello world!");
    return 0;
}
