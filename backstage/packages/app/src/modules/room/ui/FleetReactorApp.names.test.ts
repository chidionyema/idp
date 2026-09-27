/**
 * FleetReactorApp.tsx is `// @ts-nocheck`, so tsc never saw that the /stream effect assigned
 * `es = new EventSource(...)` with no `let es` anywhere. The ReferenceError was swallowed by the
 * connect() catch, onmessage was never set, and /fleet received no stream frame at all: no
 * sessions, no cinema cues, no news stories. The blast toggle read an undeclared `selectedNode`
 * the same way. The file stays nocheck; the one class of error that silently kills it does not.
 */
import * as fs from 'fs';
import * as path from 'path';
import * as ts from 'typescript';

const FILE = path.join(__dirname, 'FleetReactorApp.tsx');
const UNDECLARED = new Set([2304, 2552]); // Cannot find name 'x' / ... Did you mean 'y'?

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
  const undeclared = ts
    .getPreEmitDiagnostics(prog, prog.getSourceFile(FILE))
    .filter(d => UNDECLARED.has(d.code))
    .map(d => {
      const { line } = d.file!.getLineAndCharacterOfPosition(d.start!);
      return `${line + 1}: ${ts.flattenDiagnosticMessageText(d.messageText, ' ')}`;
    });
  expect(undeclared).toEqual([]);
}, 60000);
