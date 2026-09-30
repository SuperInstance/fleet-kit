from PKG.canary import (CANARY_HEX, FLEET_CANARY, ACCENTED_TRAP, ALPHABET_CANARY,
                        fnv1a64, alphabet_canary)
OPC = ["BIND","LINK","EFFECT","VIEW","TICK","ATTEST","DELEGATE","CONTEST","MERGE","REVOKE","WITHDRAW"]

def test_byte_canary():
    assert fnv1a64(CANARY_HEX) == FLEET_CANARY
    # Compare the INTEGER, never the text.
    #
    # The fleet writes the canary as 0x024a555471370b18d -- SEVENTEEN hex digits. A u64
    # prints sixteen. The leading zero is insignificant to the value, which is why nobody
    # noticed, but it means a padded 16-digit form and the fleet's own literal are
    # different STRINGS for the same number. Python hex(), Rust {:X} and JS toString(16)
    # all strip it; every hand-written copy keeps it. Text comparison is a trap here.
    assert fnv1a64(CANARY_HEX) == 0x024A555471370B18D

def test_unaccented_twin_is_not_the_canary():
    assert fnv1a64("cafe Δ 日本語") == ACCENTED_TRAP
    assert fnv1a64("cafe Δ 日本語") != FLEET_CANARY

def test_alphabet_canary():
    assert alphabet_canary(OPC) == ALPHABET_CANARY

def test_NEGATIVE_CONTROL_renaming_an_opcode_moves_the_pin():
    """Break it on purpose and watch the pin move. Paste both outputs in the PR."""
    assert alphabet_canary([*OPC[:8], "MERGER", *OPC[9:]]) != ALPHABET_CANARY
    assert alphabet_canary(OPC) == ALPHABET_CANARY
