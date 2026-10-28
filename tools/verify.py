#!/usr/bin/env python3
"""Check a built sample against its facts.json (the answer key).

Each fact is a claim about the binary that you could make while reversing
it: what it prints, which strings it contains, which sections and symbols it
has, what a function's disassembly looks like. This script proves or
disproves each claim, and writes a disassembly listing plus a SHA-256 of the
binary so a finding can be tied to the exact file it was made on.

Fact kinds (every fact may also have "toolchain" and "level" filters):
  run             {"args": [...], "stdout": "...", "exit_code": 0}
  strings_present {"values": ["..."]}   byte strings found in the file
  strings_absent  {"values": ["..."]}
  sections        {"values": [".text", ...]}   read by the parser below
  symbols         {"values": ["vtable for Circle", ...]}   GCC (nm -C)
  disasm          {"function": "main", "contains": [regex], "absent": [regex]}
                  GCC (objdump); a regex matches one instruction line
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path


# --- Section headers, read directly from the file ---------------------------
# Kept small on purpose: it is the same layout a disassembler parses first.

def pe_sections(data: bytes) -> list[str]:
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ValueError("missing PE signature")
    count = struct.unpack_from("<H", data, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
    table = pe_offset + 24 + optional_size
    names = []
    for i in range(count):
        raw = data[table + 40 * i: table + 40 * i + 8]
        names.append(raw.rstrip(b"\0").decode("ascii", "replace"))
    return names


def elf_sections(data: bytes) -> list[str]:
    if data[4] != 2 or data[5] != 1:
        raise ValueError("only 64-bit little-endian ELF is supported")
    shoff = struct.unpack_from("<Q", data, 0x28)[0]
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", data, 0x3A)
    def header(i: int) -> tuple[int, int]:
        base = shoff + i * shentsize
        name = struct.unpack_from("<I", data, base)[0]
        offset = struct.unpack_from("<Q", data, base + 0x18)[0]
        return name, offset
    strtab = header(shstrndx)[1]
    names = []
    for i in range(1, shnum):
        start = strtab + header(i)[0]
        names.append(data[start:data.index(b"\0", start)].decode("ascii", "replace"))
    return names


def sections(data: bytes) -> list[str]:
    if data[:2] == b"MZ":
        return pe_sections(data)
    if data[:4] == b"\x7fELF":
        return elf_sections(data)
    raise ValueError("not a PE or ELF file")


# --- GCC tooling helpers -----------------------------------------------------

def tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"{name} not found on PATH")
    return path


def defined_symbols(binary: Path) -> set[str]:
    out = subprocess.run([tool("nm"), "-C", "--defined-only", str(binary)],
                         check=True, capture_output=True, text=True).stdout
    symbols = set()
    for line in out.splitlines():
        parts = line.split(maxsplit=2)
        if len(parts) == 3:
            symbols.add(parts[2])
    return symbols


def disassemble(binary: Path) -> str:
    return subprocess.run(
        [tool("objdump"), "-d", "-C", "--no-show-raw-insn", "-M", "intel", str(binary)],
        check=True, capture_output=True, text=True).stdout


def functions(listing: str) -> dict[str, list[str]]:
    """Split an objdump listing into {demangled name: instruction lines}."""
    result: dict[str, list[str]] = {}
    current = None
    for line in listing.splitlines():
        header = re.match(r"^[0-9a-f]+ <(.+)>:$", line)
        if header:
            current = header.group(1)
            result[current] = []
        elif current is not None and line.strip():
            result[current].append(line.strip())
    return result


def find_function(table: dict[str, list[str]], name: str) -> list[str]:
    # Accept "check" for "(anonymous namespace)::check(char const*)" so facts
    # stay readable.
    for key, body in table.items():
        if key == name or re.search(rf"(^|::){re.escape(name)}\(", key):
            return body
    raise KeyError(f"function {name!r} not in disassembly")


# --- Checks -----------------------------------------------------------------

class Report:
    def __init__(self) -> None:
        self.failures = 0

    def result(self, ok: bool, message: str) -> None:
        print(("PASS " if ok else "FAIL ") + message)
        if not ok:
            self.failures += 1


def check_fact(fact: dict, binary: Path, data: bytes, report: Report, cache: dict) -> None:
    kind = fact["kind"]
    if kind == "run":
        args = fact.get("args", [])
        proc = subprocess.run([str(binary), *args], capture_output=True, text=True, timeout=30)
        stdout = proc.stdout.replace("\r\n", "\n")
        label = f"run {args}"
        if "stdout" in fact:
            report.result(stdout == fact["stdout"],
                          f"{label}: stdout" + ("" if stdout == fact["stdout"]
                                                else f" was {stdout!r}, expected {fact['stdout']!r}"))
        expected_code = fact.get("exit_code", 0)
        report.result(proc.returncode == expected_code,
                      f"{label}: exit code {proc.returncode} (expected {expected_code})")
    elif kind in ("strings_present", "strings_absent"):
        want = kind == "strings_present"
        for value in fact["values"]:
            found = value.encode() in data
            report.result(found == want, f"string {value!r} {'present' if found else 'absent'}")
    elif kind == "sections":
        names = sections(data)
        for value in fact["values"]:
            report.result(value in names, f"section {value} (file has {', '.join(names)})")
    elif kind == "symbols":
        if "symbols" not in cache:
            cache["symbols"] = defined_symbols(binary)
        for value in fact["values"]:
            report.result(value in cache["symbols"], f"symbol {value!r} defined")
    elif kind == "disasm":
        if "functions" not in cache:
            cache["functions"] = functions(disassemble(binary))
        name = fact["function"]
        try:
            body = find_function(cache["functions"], name)
        except KeyError as error:
            report.result(False, str(error))
            return
        for pattern in fact.get("contains", []):
            hit = any(re.search(pattern, line) for line in body)
            report.result(hit, f"{name}: has an instruction matching /{pattern}/")
        for pattern in fact.get("absent", []):
            hit = any(re.search(pattern, line) for line in body)
            report.result(not hit, f"{name}: no instruction matching /{pattern}/")
    else:
        report.result(False, f"unknown fact kind {kind!r}")


def write_listing(binary: Path, toolchain: str, listings: Path, digest: str) -> None:
    listings.mkdir(parents=True, exist_ok=True)
    (listings / f"{binary.stem}.sha256").write_text(f"{digest}  {binary.name}\n")
    if toolchain == "gcc":
        text = disassemble(binary)
    elif shutil.which("dumpbin"):
        text = subprocess.run(["dumpbin", "/nologo", "/disasm", "/headers", str(binary)],
                              capture_output=True, text=True).stdout
    else:
        return
    (listings / f"{binary.stem}.asm.txt").write_text(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--facts", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--level", required=True, choices=["O0", "O2"])
    parser.add_argument("--toolchain", required=True, choices=["gcc", "msvc"])
    parser.add_argument("--listings", type=Path)
    args = parser.parse_args()

    data = args.binary.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    print(f"binary  {args.binary.name}  sha256 {digest}")
    print(f"build   {args.toolchain} {args.level}")
    if args.listings:
        write_listing(args.binary, args.toolchain, args.listings, digest)

    facts = json.loads(args.facts.read_text())
    report = Report()
    cache: dict = {}
    checked = 0
    for fact in facts["facts"]:
        if fact.get("toolchain", args.toolchain) != args.toolchain:
            continue
        if fact.get("level", args.level) != args.level:
            continue
        checked += 1
        check_fact(fact, args.binary, data, report, cache)
    if checked == 0:
        report.result(False, "no facts apply to this build")
    print(f"{report.failures} failure(s)")
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
