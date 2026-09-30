// The fleet canary, and the alphabet canary that should have existed all along.
//
// The byte canary is applied to a FIXTURE STRING. It is not applied to the opcode names.
// That is how `MERGER` survived in the package that defines the canon: the conservation
// law was checked where the numbers are, and the alphabet was unchecked.
export const CANARY_HEX        = 'café Δ 日本語';
export const FLEET_CANARY      = 0x024a555471370b18dn;
export const ACCENTED_TRAP     = 0xFEE91CF40962B966n;   // the unaccented twin; never a canary

const M = (1n << 64n) - 1n;
export function fnv1a64(s) {
  let h = 14695981039346656037n;
  for (const b of new TextEncoder().encode(s)) h = ((h ^ BigInt(b)) * 1099511628211n) & M;
  return h;
}

/** The byte canary: proves the fixture hashed the same way in every runtime. */
export const computedCanary = fnv1a64(CANARY_HEX);

/** The alphabet canary: proves the NAMES of the substrate are unchanged.
    One line of input, and it is what would have caught MERGER on the day it shipped. */
export function alphabetCanary(opcodes, sep = '|') {
  return fnv1a64([...opcodes].slice().sort().join(sep));
}
