// Sample 02: a small "crackme" you built yourself.
//
// The password is never stored as plain text: it is XOR-encoded, so running
// `strings` on the binary does not reveal it. Your job is to recover it from
// the disassembly (find the comparison loop and the encoded bytes), then
// confirm with the program. The answer is in facts.json; look only after.
//
// Then compare the O0 and O2 builds. GCC at O2 notices that
// (input ^ key) ^ encoded == 0 is the same as input == (encoded ^ key), works
// out encoded ^ key at build time, and stores the plain password in .rodata.
// The optimiser removed your obfuscation: facts.json checks this too.
#include <cstdio>
#include <cstring>

namespace {

constexpr unsigned char kKey = 0x5A;
// The password XORed with kKey, byte by byte.
constexpr unsigned char kEncoded[] = {0x2F, 0x34, 0x36, 0x35, 0x39, 0x31, 0x6E, 0x68};

bool check(const char* input) {
    if (std::strlen(input) != sizeof(kEncoded)) return false;
    unsigned char diff = 0;
    for (std::size_t i = 0; i < sizeof(kEncoded); ++i) {
        diff |= static_cast<unsigned char>(input[i] ^ kKey) ^ kEncoded[i];
    }
    return diff == 0;
}

} // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::printf("usage: crackme <password>\n");
        return 2;
    }
    if (check(argv[1])) {
        std::printf("Access granted\n");
        return 0;
    }
    std::printf("Access denied\n");
    return 1;
}
