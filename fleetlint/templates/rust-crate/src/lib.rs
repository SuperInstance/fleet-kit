//! The canary, with no dependencies.
pub const CANARY_HEX: &str = "caf\u{e9} \u{394} \u{65e5}\u{672c}\u{8a9e}";
pub const FLEET_CANARY: u64 = 0x024a_5554_7137_0b18d;
pub const ACCENTED_TRAP: u64 = 0xfee9_1cf4_0962_b966;
pub const ALPHABET_CANARY: u64 = 0xE5C271EE5C13E9C7;   // sorted opcodes joined by '|'

pub fn fnv1a64(s: &str) -> u64 {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    for b in s.as_bytes() { h ^= *b as u64; h = h.wrapping_mul(0x100_0000_01b3); }
    h
}

pub fn alphabet_canary<S: AsRef<str>>(opcodes: &[S], sep: &str) -> u64 {
    let mut v: Vec<&str> = opcodes.iter().map(|s| s.as_ref()).collect();
    v.sort_unstable();
    fnv1a64(&v.join(sep))
}
