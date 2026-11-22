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
code = code.replace(/\)\s*:\s*(?:[^{}]|\{[^{}]*\})*\s*\{/g, ") {");

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
  params.replace(/:\s*[\w<>\[\]?|.,\s]+?(?=,|\)|$)/g, "");
code = code.replace(/(\bfunction\s+\w+\s*)\(([^()]*)\)/g, (m, head, params) => `${head}(${stripParamTypes(params)})`);
code = code.replace(/(\bconstructor\s*)\(([^()]*)\)/g, (m, head, params) => `${head}(${stripParamTypes(params)})`);
code = code.replace(/(^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?[\w$]+\s*)\(([^()]*)\)\s*\{/gm, (m, head, params) =>
  head.trimEnd().endsWith("=") ? m : `${head}(${stripParamTypes(params)}) {`);

// 8. Strip simple type annotations from const/let/var declarations
code = code.replace(/(const|let|var)\s+\w+\s*:[^=]*= /g, "$1 ");

const outFile = out || src.replace(/\.ts$/, ".js");
fs.writeFileSync(outFile, code);
console.log(`Transpiled: ${src} -> ${outFile}`);