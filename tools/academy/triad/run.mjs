#!/usr/bin/env node
import { getLesson, getAssessment } from './lesson.mjs';
import { assessTransfer } from './evaluate.mjs';
const mode = process.argv[2] || '--help';
if (mode === '--lesson') console.log(JSON.stringify(getLesson(), null, 2));
else if (mode === '--assessment') console.log(JSON.stringify(getAssessment(), null, 2));
else if (mode === '--score') {
  let text = '';
  for await (const chunk of process.stdin) {
    text += chunk;
    if (text.length > 16_384) { console.error('REFUSED: oversized answer payload'); process.exitCode = 2; break; }
  }
  if (!process.exitCode) {
    try { console.log(JSON.stringify(assessTransfer(JSON.parse(text)), null, 2)); }
    catch (err) { console.error('REFUSED: ' + err.message); process.exitCode = 2; }
  }
} else {
  console.log('TRIAD research pilot (zero telemetry): --lesson | --assessment | --score (JSON stdin)');
  if (mode !== '--help') process.exitCode = 2;
}
