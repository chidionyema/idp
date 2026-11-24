#!/usr/bin/env node
/**
 * Simple TypeScript -> JavaScript transpiler for meridian-router-edge.
 *
 * Handles the subset of TypeScript used in this project:
 * - Removes `export interface X { ... }` and `interface X { ... }` blocks
 * - Removes `export type X = ...` lines
 * - Removes `import type { ... } from "..."` lines
 * - Removes return type annotations from functions/methods
 * - Strips class property modifiers (private, readonly) and type annotations
 * - Strips `implements X` clauses
 *
 * Usage: node scripts/transpile.mjs <src-file.ts> [out-file.js]
 */
import fs from "node:fs";

const src = process.argv[2];
const out = process.argv[3];

if (!src) {
  console.error("Usage: node scripts/transpile.mjs <src-file.ts> [out-file.js]");
  process.exit(1);
}

let code = fs.readFileSync(src, "utf8");

// 1. Remove import type lines entirely
code = code.replace(/^import type \{[^}]*\} from "[^"]*";\s*\n?/gm, "");

// 2. Remove all interface blocks (exported and not)
code = code.replace(/^(export\s+)?interface [\w<>,\s]+\s*\{[\s\S]*?^\}\s*\n?/gm, "");

// 3. Remove export type lines
code = code.replace(/^export type \w+[^;]*;\s*\n?/gm, "");

// 4. Remove return type annotations: `): Promise<X> {` / `): Promise<{ok: b}> {` -> `) {`
//    The type span must stay on one line and contain no parens or semicolons:
//    crossing newlines let it swallow entire following signatures (bisect 2026-11-22).
code = code.replace(/\)\s*:\s*[^{}();\n]*(?:\{[^{}\n]*\}[^{}();\n]*)*\{/g, ") {");

// 5. Remove `implements X` from class declarations
code = code.replace(/implements\s+[\w\s,]+/g, "");

// 6. Strip class property modifiers and type annotations:
//    `private readonly state: DurableObjectState;` → `state;`
code = code.replace(/\b(private|public|protected)\s+/g, "");
code = code.replace(/\breadonly\s+/g, "");
code = code.replace(/^\s*(\w+)\s*:\s*[\w<>\[\]?|.]+\s*;\s*$/gm, "$1;");

// 7. Strip parameter type annotations from function/method declarations
//    `function utcDay(nowMs: number) {` → `function utcDay(nowMs) {`
//    Handles the space after the colon, unions and generics, constructors, class
//    methods and arrow assignments -- never call sites, where `:` is an object key.
const stripParamTypes = (params) =>
  params
    .replace(/\?\s*:/g, ":")
    .replace(/:\s*(?:"[^"]*"|[\w<>\[\]?|.,\s])+?(?=,|\)|$)/g, "");
code = code.replace(/(\bfunction\s+\w+\s*)\(([^()]*)\)/g, (m, head, params) => `${head}(${stripParamTypes(params)})`);
code = code.replace(/(\bconstructor\s*)\(([^()]*)\)/g, (m, head, params) => `${head}(${stripParamTypes(params)})`);
code = code.replace(/(^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?[\w$]+\s*)\(([^()]*)\)\s*\{/gm, (m, head, params) =>
  head.trimEnd().endsWith("=") ? m : `${head}(${stripParamTypes(params)}) {`);

// 8. Strip simple type annotations from const/let/var declarations
//    `const chunks: Uint8Array[] = [];` -> `const chunks = [];` (name is captured,
//    not dropped: the old replacement emitted `const [];`, node --check caught it)
code = code.replace(/(const|let|var)\s+(\w+)\s*:[^=\n]*=\s*/g, "$1 $2 = ");

// 8b. Declarations without initializer: `let body: ChatCompletionRequest;` -> `let body;`
code = code.replace(/(const|let|var)\s+(\w+)\s*:\s*[\w<>\[\]?|.]+\s*;/g, "$1 $2;");

// 10. Generic type arguments on new/call expressions:
//     `new TransformStream<Uint8Array, Uint8Array>()` -> `new TransformStream()`
code = code.replace(/\b(new\s+[\w.$]+)\s*<[^()]*>\s*\(/g, "$1(");
code = code.replace(/\b([A-Za-z_$][\w$.]*)<[\w$<>,.\[\]\s]*>\(/g, "$1(");

// 8b. Declarations without initializer: `let body: ChatCompletionRequest;` -> `let body;`
code = code.replace(/(const|let|var)\s+(\w+)\s*:\s*[\w<>\[\]?|.]+\s*;/g, "$1 $2;");

// 10. Generic type arguments on new/call expressions:
//     `new TransformStream<Uint8Array, Uint8Array>()` -> `new TransformStream()`
code = code.replace(/\b(new\s+[\w.$]+)\s*<[^()]*>\s*\(/g, "$1(");
code = code.replace(/\b([A-Za-z_$][\w$.]*)<[\w$<>,.\[\]\s]*>\(/g, "$1(");

// 8b. Declarations without initializer: `let body: ChatCompletionRequest;` -> `let body;`
code = code.replace(/(const|let|var)\s+(\w+)\s*:\s*[\w<>\[\]?|.]+\s*;/g, "$1 $2;");

// 10. Generic type arguments on new/call expressions:
//     `new TransformStream<Uint8Array, Uint8Array>()` -> `new TransformStream()`
code = code.replace(/\b(new\s+[\w.$]+)\s*<[^()]*>\s*\(/g, "$1(");
code = code.replace(/\b([A-Za-z_$][\w$.]*)<[\w$<>,.\[\]\s]*>\(/g, "$1(");

// 8b. Declarations without initializer: `let body: ChatCompletionRequest;` -> `let body;`
code = code.replace(/(const|let|var)\s+(\w+)\s*:\s*[\w<>\[\]?|.]+\s*;/g, "$1 $2;");

// 10. Generic type arguments on new/call expressions:
//     `new TransformStream<Uint8Array, Uint8Array>()` -> `new TransformStream()`
code = code.replace(/\b(new\s+[\w.$]+)\s*<[^()]*>\s*\(/g, "$1(");
code = code.replace(/\b([A-Za-z_$][\w$.]*)<[\w$<>,.\[\]\s]*>\(/g, "$1(");

// 9. Strip `as` type assertions: `(await r.json()) as { roles: X }` -> `(await r.json())`
{
  // Balanced-brace scan: a lazy regex here crossed try blocks; this cannot.
  let out = "", i = 0;
  while (i < code.length) {
    const m = code.slice(i).match(/^\s+as\s*\{/);
    if (!m) { out += code[i++]; continue; }
    let j = i + m[0].length, depth = 1;
    while (j < code.length && depth > 0) {
      if (code[j] === "{") depth++;
      else if (code[j] === "}") depth--;
      j++;
    }
    let k = j;
    while (k < code.length && /\s/.test(code[k])) k++;
    if (";,)".includes(code[k] ?? "")) { i = j; continue; }
    out += code[i++];
  }
  code = out;
}
code = code.replace(/\s+as\s+(?:const|[\w$][\w<>\[\]$?|.]*)/g, "");

// 8b. Declarations without initializer: `let body: ChatCompletionRequest;` -> `let body;`
code = code.replace(/(const|let|var)\s+(\w+)\s*:\s*[\w<>\[\]?|.]+\s*;/g, "$1 $2;");

// 10. Generic type arguments on new/call expressions:
//     `new TransformStream<Uint8Array, Uint8Array>()` -> `new TransformStream()`
code = code.replace(/\b(new\s+[\w.$]+)\s*<[^()]*>\s*\(/g, "$1(");
code = code.replace(/\b([A-Za-z_$][\w$.]*)<[\w$<>,.\[\]\s]*>\(/g, "$1(");

// 8b. Declarations without initializer: `let body: ChatCompletionRequest;` -> `let body;`
code = code.replace(/(const|let|var)\s+(\w+)\s*:\s*[\w<>\[\]?|.]+\s*;/g, "$1 $2;");

// 10. Generic type arguments on new/call expressions:
//     `new TransformStream<Uint8Array, Uint8Array>()` -> `new TransformStream()`
code = code.replace(/\b(new\s+[\w.$]+)\s*<[^()]*>\s*\(/g, "$1(");
code = code.replace(/\b([A-Za-z_$][\w$.]*)<[\w$<>,.\[\]\s]*>\(/g, "$1(");

// 9. Strip `as` type assertions: `(await r.json()) as { roles: X }` -> `(await r.json())`
code = code.replace(/\s+as\s*\{[\s\S]*?\}(?=\s*[;,)])/g, "");
code = code.replace(/\s+as\s+(?:const|[\w$][\w<>\[\]$?|.]*)/g, "");

const outFile = out || src.replace(/\.ts$/, ".js");
fs.writeFileSync(outFile, code);
console.log(`Transpiled: ${src} -> ${outFile}`);