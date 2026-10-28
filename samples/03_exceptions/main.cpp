// Sample 03: C++ exceptions.
//
// What to look for in a disassembler:
//  * `throw` becomes a call that allocates the exception object and then
//    raises it (__cxa_allocate_exception / __cxa_throw on GCC,
//    _CxxThrowException on MSVC);
//  * the catch handler is not reached by any normal jump: the unwinder finds
//    it through tables (.gcc_except_table + .eh_frame on GCC, .pdata/.xdata
//    on x64 Windows);
//  * the exception's type is matched with the same RTTI used by typeid.
#include <cstdio>
#include <stdexcept>
#include <string>

struct ParseError : std::runtime_error {
    ParseError(const std::string& what, int column)
        : std::runtime_error(what), column(column) {}
    int column;
};

int parse_digit(const char* text, int column) {
    char c = text[column];
    if (c < '0' || c > '9') throw ParseError("not a digit", column);
    return c - '0';
}

int sum_digits(const char* text) {
    int sum = 0;
    for (int i = 0; text[i] != '\0'; ++i) sum += parse_digit(text, i);
    return sum;
}

int main() {
    const char* inputs[] = {"1234", "12x4"};
    int failures = 0;
    for (const char* input : inputs) {
        try {
            std::printf("%s -> %d\n", input, sum_digits(input));
        } catch (const ParseError& e) {
            std::printf("%s -> error: %s at column %d\n", input, e.what(), e.column);
            ++failures;
        }
    }
    return failures;
}
