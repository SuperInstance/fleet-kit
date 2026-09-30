"""The fleet canary, and the alphabet canary.

The byte canary (0x024a555471370b18d) hashes a FIXTURE STRING and is applied in 20+
repositories. It has never once been applied to the NAMES. That is how MERGER survived
in the package that defines the canon: the conservation law was checked where the numbers
are, and the alphabet was unchecked.
"""
CANARY_HEX = "café Δ 日本語"
FLEET_CANARY = 0x024A555471370B18D
ACCENTED_TRAP = 0xFEE91CF40962B966      # the unaccented twin; never a canary
ALPHABET_CANARY = 0xE5C271EE5C13E9C7                 # sorted opcodes joined by '|'

def fnv1a64(s: str) -> int:
    h = 0xCBF29CE484222325
    for b in s.encode("utf-8"):          # utf-8 EXPLICIT — a bare .encode() is the trap
        h = ((h ^ b) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h

def alphabet_canary(opcodes, sep: str = "|") -> int:
    return fnv1a64(sep.join(sorted(opcodes)))
