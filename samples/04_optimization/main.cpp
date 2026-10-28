// Sample 04: what the optimiser does to your code.
//
// Compare 04_optimization_O0 with 04_optimization_O2:
//  * at O0, main() calls sum_to() and sum_to() runs a real loop;
//  * at O2, sum_to() is inlined and disappears as a function. The first call
//    is folded into one constant (the compiler knows the answer at build
//    time), so main() just passes 5050 (0x13ba) to printf;
//  * the volatile read cannot be known at build time, so the second call
//    keeps a real loop, now written out inside main() (often unrolled).
#include <cstdio>

static int sum_to(int n) {
    int total = 0;
    for (int i = 1; i <= n; ++i) total += i;
    return total;
}

volatile int g_runtime_n = 10;

int main() {
    std::printf("sum_to(100) = %d\n", sum_to(100));
    std::printf("sum_to(runtime) = %d\n", sum_to(g_runtime_n));
    return 0;
}
