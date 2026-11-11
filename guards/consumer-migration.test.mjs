import test from 'node:test';
import assert from 'node:assert/strict';
import { migrationAdmission } from './consumer-migration.mjs';
const overdue='2026-10-31', today='2026-11-11';
test('expired legacy migration does not veto unrelated release when its stylesheet is untouched', () => {
  const a=migrationAdmission({hasImport:false,migrationDeadline:overdue,today,stylesheetChanged:false});
  assert.equal(a.accept,true);
  assert.match(a.reason,/overdue/);
});
test('expired legacy consumer altering CSS without kit fails closed', () => {
  const a=migrationAdmission({hasImport:false,migrationDeadline:overdue,today,stylesheetChanged:true});
  assert.equal(a.accept,false);
  assert.match(a.reason,/changed/);
});
test('missing Git baseline cannot turn non-compliance into a waiver', () => {
  assert.equal(migrationAdmission({hasImport:false,migrationDeadline:overdue,today,stylesheetChanged:null}).accept,false);
});
test('all new consumers must import kit', () => {
  assert.equal(migrationAdmission({hasImport:false,today,stylesheetChanged:false}).accept,false);
});
test('legacy within migration window still warns without blocking', () => {
  assert.equal(migrationAdmission({hasImport:false,migrationDeadline:'2026-12-15',today,stylesheetChanged:null}).accept,true);
});
test('existing import is subject to dependency and brand validation by importer', () => {
  assert.equal(migrationAdmission({hasImport:true,migrationDeadline:overdue,today,stylesheetChanged:true}).accept,true);
});
