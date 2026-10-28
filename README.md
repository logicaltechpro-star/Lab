# Lab

A small, reproducible reverse-engineering lab for studying C++. Every binary
here is built from source in this repository, so you always know what the
right answer is, and every claim you make about a binary can be checked by a
test.

## How it works

Each sample in `samples/` is one short C++ program that shows one topic. It
is built twice, unoptimised (`_O0`) and optimised (`_O2`), so you can see
what the compiler does to the same code.

Next to each program is a `facts.json`: the answer key. A fact is a claim you
could make while reversing the binary, such as "it prints this", "the
password is not stored as plain text", "main() calls the area() slot of the
vtable through `[rax+0x10]`". `tools/verify.py` checks every fact against
the built file and prints PASS or FAIL for each one, with the binary's
SHA-256, so a result is tied to the exact file it was made on.

| Sample | Topic | What the facts prove |
|---|---|---|
| `01_vtables` | Virtual functions, vtables, RTTI | vtable and typeinfo records exist; virtual calls go through vtable slots 2 and 3 at O2; `dynamic_cast` calls the runtime |
| `02_crackme` | Recovering a hidden password | the XOR-encoded password is absent at O0, and GCC's optimiser puts it back in plain text at O2 |
| `03_exceptions` | How `throw` and `catch` are compiled | `__cxa_throw` is called; unwind tables (`.eh_frame`, `.gcc_except_table`, or `.pdata` on Windows) are present |
| `04_optimization` | Inlining and constant folding | at O0 `main` calls `sum_to`; at O2 the call is gone and the answer 5050 (`0x13ba`) is a constant |

## Build and verify

Linux (GCC, all facts are checked):

```sh
sudo apt install g++ cmake ninja-build binutils python3
cmake --preset linux-gcc
cmake --build --preset linux-gcc
ctest --preset linux-gcc
```

Windows (MSVC, from a "x64 Native Tools Command Prompt for VS 2022"):

```bat
cmake --preset msvc
cmake --build --preset msvc
ctest --preset msvc
```

On Windows only the facts that do not depend on GCC are checked (program
output, strings, PE sections). Binaries land in `build/<preset>/bin/`, and a
disassembly listing plus a `.sha256` for each one land in
`build/<preset>/listings/`.

CI runs both builds on every push and uploads the binaries and listings as
artifacts, so each result has a public, repeatable record.

## Tools for the exercises

All free, and all used only on the binaries you build here.

| Tool | Use it for | Platform |
|---|---|---|
| [Ghidra](https://ghidra-sre.org/) | Disassembly and decompilation, both ELF and PE | Windows, Linux, macOS |
| `objdump -d -C -M intel`, `nm -C`, `readelf -S` | Quick listings, symbols, sections of ELF files | Linux |
| `gdb` | Stepping through the Linux builds | Linux |
| [x64dbg](https://x64dbg.com/) | Stepping through the Windows builds | Windows |
| WinDbg | Microsoft's debugger, reads the PDBs from the MSVC build | Windows |
| [PE-bear](https://github.com/hasherezade/pe-bear) | Viewing PE headers, sections and imports | Windows, Linux |
| `dumpbin /headers /disasm` | MSVC's own PE dumper | Windows |

## Adding your own sample

1. Make `samples/05_name/main.cpp` with a comment at the top saying what to
   look for.
2. Add `re_lab_sample(05_name)` to `CMakeLists.txt`.
3. Write `samples/05_name/facts.json`. Start with a `run` fact, then add one
   fact for each thing you found in the disassembler. The fact kinds are
   listed at the top of `tools/verify.py`.
4. Run `ctest`. If a fact fails, either your analysis or your fact is wrong;
   both are worth knowing.

Record each investigation with the template in
[`notebook/TEMPLATE.md`](notebook/TEMPLATE.md).
