/**
 * FleetReactorApp.tsx is `// @ts-nocheck`, so tsc never saw that the /stream effect assigned
 * `es = new EventSource(...)` with no `let es` anywhere. The ReferenceError was swallowed by the
 * connect() catch, onmessage was never set, and /fleet received no stream frame at all: no
 * sessions, no cinema cues, no news stories. The blast toggle read an undeclared `selectedNode`
 * the same way. The file stays nocheck; the one class of error that silently kills it does not.
 *
 * Nor does the other half of it: a name declared TWICE in one scope (2026-10-20, idp#6709). The
 * attention rail added `const [signals, setSignals]` to a component that already had one; tsc
 * never saw it, the bundle shipped `const[ek,...]` beside `function ek`, and the browser refused
 * to parse the whole chunk -- /fleet was a ChunkLoadError in production.
 */
import * as fs from 'fs';
import * as path from 'path';
import * as ts from 'typescript';

const FILE = path.join(__dirname, 'FleetReactorApp.tsx');
const UNDECLARED = new Set([2304, 2552]); // Cannot find name 'x' / ... Did you mean 'y'?
const REDECLARED = new Set([2451, 2300]); // Cannot redeclare block-scoped variable / Duplicate identifier

it('FleetReactorApp uses no name it never declared', () => {
  const opts: ts.CompilerOptions = {
    noEmit: true,
    noResolve: true,
    types: [],
    jsx: ts.JsxEmit.ReactJSX,
    target: ts.ScriptTarget.ES2020,
    lib: ['lib.es2020.d.ts', 'lib.dom.d.ts'],
    skipLibCheck: true,
  };
  const host = ts.createCompilerHost(opts);
  const read = host.getSourceFile;
  host.getSourceFile = (f, lang, ...rest) =>
    f === FILE
      ? ts.createSourceFile(f, fs.readFileSync(f, 'utf8').replace('// @ts-nocheck', ''), lang, true)
      : read(f, lang, ...rest);
  const prog = ts.createProgram([FILE], opts, host);
  const diags = ts.getPreEmitDiagnostics(prog, prog.getSourceFile(FILE));
  const at = (d: ts.Diagnostic) => {
    const { line } = d.file!.getLineAndCharacterOfPosition(d.start!);
    return `${line + 1}: ${ts.flattenDiagnosticMessageText(d.messageText, ' ')}`;
  };
  expect(diags.filter(d => REDECLARED.has(d.code)).map(at)).toEqual([]);
  const undeclared = diags
    .filter(d => UNDECLARED.has(d.code))
    .map(at);
  expect(undeclared).toEqual([]);
}, 60000);
