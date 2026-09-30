import { test } from 'node:test';
import assert from 'node:assert/strict';
import { FLEET_CANARY, computedCanary, ACCENTED_TRAP, fnv1a64, alphabetCanary } from '../index.js';
import { ALL_OPCODES } from '@superinstance/opcode-canon';

test('byte canary: the fixture hashes to the fleet value in this runtime', () => {
  assert.equal(computedCanary, FLEET_CANARY);
  assert.equal(computedCanary, 0x024a555471370b18dn);   // compare NUMBERS, not text
});

test('the unaccented twin is NOT the canary', () => {
  assert.notEqual(fnv1a64('cafe Δ 日本語'), FLEET_CANARY);
  assert.equal(fnv1a64('cafe Δ 日本語'), ACCENTED_TRAP);
});

test('alphabet canary: the opcode NAMES are pinned', () => {
  assert.equal('0x' + alphabetCanary(ALL_OPCODES).toString(16), '0xE5C271EE5C13E9C7');
});

test('every opcode resolves to a defined value', () => {
  for (const n of ALL_OPCODES) assert.notEqual((await import('../index.js')).byName[n], undefined, n);
});

test('NEGATIVE CONTROL — see templates/_shared/negative_control.md', async (t) => {
  t.diagnostic('break the alphabet, confirm the pinned value moves, restore, confirm it returns');
  const before = alphabetCanary(ALL_OPCODES);
  const drifted = alphabetCanary([...ALL_OPCODES].map((n) => (n === 'MERGE' ? 'MERGER' : n)));
  assert.notEqual(drifted, before, 'a renamed opcode MUST move the alphabet canary');
  assert.equal(alphabetCanary(ALL_OPCODES), before, 'and must return when restored');
});
