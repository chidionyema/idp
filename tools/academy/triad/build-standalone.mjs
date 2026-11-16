#!/usr/bin/env node
/**
 * Reproducibly assemble the tested TRIAD studio into one offline HTML artifact.
 * A build step, not an alternate curriculum, scoring path or deployment.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.dirname(fileURLToPath(import.meta.url));
const target = process.argv[2] || path.join(root, 'triad-standalone.html');
const files = ['lesson.mjs', 'adaptive.mjs', 'studio.mjs'];

function inlineSource(name) {
  let code = readFileSync(path.join(root, name), 'utf8');
  const before = code;
  code = code.replace(/^import[^\n]*;\r?\n/gm, '');
  code = code.replace(/^export (const|function)\b/gm, '$1');
  if (/^\s*(?:import|export)\s/m.test(code)) throw new Error('Unresolved module syntax in ' + name);
  if (code.includes('</script')) throw new Error('Unsafe script closer in ' + name);
  if (!before.trim()) throw new Error('Empty source: ' + name);
  return '\n/* Inlined exact source logic: ' + name + ' */\n' + code;
}

const base = readFileSync(path.join(root, 'studio.html'), 'utf8');
const marker = '<script type="module" src="./studio.mjs"></script>';
if (base.split(marker).length !== 2) throw new Error('Studio script entry missing or ambiguous');
const combined = files.map(inlineSource).join('\n');
const result = base.replace(marker, '<script type="module">\n' + combined + '\n</script>');
if (/<script[^>]+src="https?:/i.test(result)) throw new Error('Unexpected external network script');
writeFileSync(target, result);
console.log('TRIAD_STANDALONE_WRITTEN', target, Buffer.byteLength(result));
