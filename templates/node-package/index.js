export { CANARY_HEX, FLEET_CANARY, alphabetCanary, fnv1a64 } from './templates/_shared/canary.mjs';
export { ALL_OPCODES, BASE_OPCODES, PROPOSED_OPCODES, OPCODE_SIGNATURES } from '@superinstance/opcode-canon';

// Derive, never destructure. A package that exports ARRAYS does not export one name per
// opcode; reading names out of it yields undefined, and an undefined re-export throws
// nothing. This is how eleven opcodes were undefined in substrate-foundation.
export const byName = Object.fromEntries(
  ALL_OPCODES.map((n) => [n, Object.freeze({ name: n, signatures: OPCODE_SIGNATURES[n] })]));
export const MISSING_OPCODES = ALL_OPCODES.filter((n) => !byName[n]);
if (MISSING_OPCODES.length) throw new Error(`unresolvable opcodes: ${MISSING_OPCODES}`);
