use pkgtpl::*;
#[test] fn byte_canary() { assert_eq!(fnv1a64(CANARY_HEX), FLEET_CANARY); }
#[test] fn the_fleet_literal_is_17_digits_but_prints_16() {
    // 0x024a555471370b18d has 17 hex digits. A u64 prints 16. Same number, two strings.
    assert_eq!(FLEET_CANARY, 0x024a_5554_7137_0b18d);
    // the value prints 16 digits; the literal people paste is 17. Compare NUMBERS.
    assert_eq!(format!("{:x}", fnv1a64(CANARY_HEX)).len(), 16);
    assert_eq!("024a555471370b18d".len(), 17);
}
#[test] fn unaccented_twin_is_not_the_canary() {
    assert_ne!(fnv1a64("cafe \u{394} \u{65e5}\u{672c}\u{8a9e}"), FLEET_CANARY);
    assert_eq!(fnv1a64("cafe \u{394} \u{65e5}\u{672c}\u{8a9e}"), ACCENTED_TRAP);
}
#[test] fn alphabet_pin() { assert_eq!(alphabet_canary(&["BIND","LINK","MERGE","TICK","VIEW","EFFECT","ATTEST","DELEGATE","CONTEST","REVOKE","WITHDRAW"], "|"), ALPHABET_CANARY); }
#[test] fn NEGATIVE_CONTROL_renaming_moves_the_pin() {
    assert_ne!(alphabet_canary(&["BIND","LINK","MERGER"], "|"), alphabet_canary(&["BIND","LINK","MERGE"], "|"));
}
