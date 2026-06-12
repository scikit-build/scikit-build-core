#include <stdio.h>

int main(void) {
  const char *v[] = {"0", "one", "2", "three"};
  for (int i = 0; i < 4; i++) {
    printf("%s ", v[i]);
  }
  printf("\n");
  return 0;
}
