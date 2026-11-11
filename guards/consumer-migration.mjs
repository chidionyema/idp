/**
 * Release-safe migration ratchet for established UI-kit consumers.
 * Strict for a new consumer and for any legacy stylesheet actually changed
 * after its deadline. Unchanged overdue legacy debt remains visible, but
 * cannot veto an unrelated P0 fix in a different source file.
 */
export function migrationAdmission({ hasImport, migrationDeadline, today, stylesheetChanged }) {
  if (hasImport) return { accept: true, reason: 'kit import present; verify dependency and brand' };
  if (!migrationDeadline) return { accept: false, reason: 'new consumer without kit integration' };
  if (migrationDeadline >= today) return { accept: true, reason: 'within declared migration window' };
  if (stylesheetChanged === false) return {
    accept: true,
    reason: 'overdue stylesheet unchanged in candidate against origin/main',
  };
  if (stylesheetChanged === null || stylesheetChanged === undefined) return {
    accept: false,
    reason: 'cannot verify legacy stylesheet is unchanged',
  };
  return { accept: false, reason: 'overdue stylesheet was changed without kit integration' };
}
