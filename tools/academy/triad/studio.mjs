import { startSession, currentView, submitChoice, advance, getReport, PILOT_VERSION } from './adaptive.mjs';

let session = startSession();
const $ = id => document.getElementById(id);
const content = $('content');
const phases = {
  diagnostic: ['Pilot diagnostic', 'Discover your starting model'],
  teach: ['Three perspectives', 'See the same principle in different worlds'],
  transfer: ['Unseen transfer', 'Apply the principle without the story'],
  remediation: ['Adaptive correction', 'Locate the exact misunderstanding'],
  retest: ['Fresh challenge', 'Try the idea somewhere new'],
  complete: ['Pilot evidence', 'What your answers do—and do not—establish'],
};
function node(tag, cls = '', text = null) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== null) e.textContent = String(text);
  return e;
}
function append(parent, ...children) { for (const x of children) parent.append(x); return parent; }
function paragraph(text, cls = 'muted') { return node('p', cls, text); }
function heading(text, cls = 'subhead') { return node('h2', cls, text); }
function badge(text) { return node('p', 'eyebrow', text); }
function makeButton(text, action, cls = 'btn') {
  const b = node('button', cls, text); b.type = 'button'; b.addEventListener('click', action); return b;
}
function notice(text) { return node('div', 'notice', text); }
function progress() {
  const n = session.answers.length;
  let pct = session.phase === 'diagnostic' ? n * 15 :
    session.phase === 'teach' ? 32 :
    session.phase === 'transfer' ? 37 + Math.round(session.answers.filter(a => a.phase === 'transfer').length / 3 * 47) :
    session.phase === 'remediation' ? 87 :
    session.phase === 'retest' ? 92 : 100;
  pct = Math.max(0, Math.min(100, pct));
  $('progressbar').style.width = pct + '%';
  $('progress').setAttribute('aria-valuenow', String(pct));
  $('progress-label').textContent = pct + '%';
  $('phase-title').textContent = phases[session.phase][0];
  $('phase-badge').textContent = phases[session.phase][1];
}
function renderQuestion(v) {
  append(content,
    badge(v.phase === 'diagnostic' ? 'Before the explanation · no feedback until complete' : 'Independent transfer · unseen scenario'),
    heading(v.phase === 'diagnostic' ? 'What would you expect?' : v.phase === 'retest' ? 'One more, different setting.' : 'Now make the leap.'),
    paragraph('Question ' + v.step + ' of ' + v.total + ' · ' + v.question.skill.replace(/-/g, ' '), 'note'),
    paragraph(v.question.prompt, 'problem')
  );
  const fieldset = node('fieldset', 'choices');
  const legend = node('legend', '', 'Select one answer'); fieldset.append(legend);
  const conf = node('div', 'confidence');
  const confLabel = node('label', '', 'How confident are you?');
  confLabel.htmlFor = 'confidence-slider';
  const slider = node('input');
  slider.type = 'range'; slider.min = '0'; slider.max = '100'; slider.step = '10'; slider.value = '60';
  slider.id = 'confidence-slider';
  const value = node('output', '', '60%');
  value.htmlFor = slider.id;
  slider.addEventListener('input', () => { value.value = slider.value + '%'; value.textContent = value.value; });
  append(conf, confLabel, slider, value);
  const action = makeButton('Submit response  →', () => {
    try {
      const picked = fieldset.querySelector('input[name="answer"]:checked');
      if (!picked) return;
      session = submitChoice(session, { itemId: v.question.id, choice: Number(picked.value), confidence: Number(slider.value) / 100 });
      render();
    } catch (err) { $('error').textContent = 'Response refused: ' + err.message; }
  });
  action.disabled = true;
  v.question.choices.forEach((answer, i) => {
    const label = node('label', 'choice');
    const input = node('input'); input.name='answer'; input.type='radio'; input.value=String(i); input.required=true;
    input.addEventListener('change', () => { action.disabled = false; });
    const copy = node('span', '', answer);
    label.append(input, copy);fieldset.append(label);
  });
  const errors = node('p', 'note');errors.id='error';errors.setAttribute('role', 'alert');
  const buttons = append(node('div', 'actions'), action, node('span', 'scoring', 'Answers remain in this browser tab. Nothing is transmitted.'));
  append(content, fieldset, conf, buttons, errors);
}
function teach(v) {
  append(content,
    badge('The invariant · causal structure over surface similarity'),
    heading('What survives across every representation?'),
    paragraph(v.canonical.rule),
  );
  const concept = node('div', 'concept');
  append(concept, node('p', 'eyebrow', 'Formal kernel'), node('div', 'equation', v.canonical.model), paragraph(v.canonical.boundary, 'note'));
  content.append(concept);
  const ul = node('ul', 'assumptions');
  v.canonical.assumptions.forEach(t => append(ul, node('li', '', t)));
  append(content, node('h3', '', 'What the guarantee actually requires'), ul);
  if(v.analogies.length) {
    append(content, badge('Relational alignment · different surfaces, shared structure'));
    const cards = node('div', 'analogy-grid');
    v.analogies.forEach(a => {
      const c=node('article','analogy');
      append(c, node('span','glyph', a.domain === 'Garden' ? '🌱' : '🎼'), node('h3','',a.domain), paragraph(a.statement));
      const maps = node('ul','assumptions');
      a.correspondences.forEach(([from,to])=> append(maps,node('li','', from+' ↔ '+to)));
      append(c,maps,paragraph('Where the analogy breaks: '+a.breaksAt,'limit'));
      cards.append(c);
    });
    append(content,cards);
    append(content,node('div','core','Shared structural principle: '+v.sharedCore));
  }
  append(content,notice('The analogy is a bridge, not evidence. A visually compelling story cannot restore lost information or grant authority.'));
  append(content,append(node('div','actions'),makeButton('Test transfer in a new domain  →', () => {session=advance(session);render();})));
}
function remedy(v) {
  append(content,
    badge('Misconception-specific correction'),
    heading('A different viewpoint may expose the gap.'),
    paragraph('Your first transfer set exposed a problem with: ' + v.missedSkills.join(', ').replaceAll('-', ' ') + '. This is feedback, not a judgement about your ability.'),
  );
  const c=node('section','analogy');
  append(c,node('span','glyph','✦'),node('h3','',v.correction.analogy),paragraph(v.correction.explanation),paragraph('Important limit: '+v.correction.limit,'limit'));
  append(content,c,paragraph('The next question uses a different setting from the one that triggered this explanation.'));
  append(content,append(node('div','actions'),makeButton('Try an unseen retest  →',()=>{session=advance(session);render();})));
}
function metric(title, value) {
  const c=node('div','metric');append(c,node('b','',value),node('span','',title));return c;
}
function result() {
  const r=getReport(session);
  append(content,badge('Evidence · never self-award mastery'),heading('You completed a real transfer exercise.'));
  const stats=node('div','split');
  append(stats,metric('Before teaching · diagnostic',r.diagnostic.correct+'/'+r.diagnostic.total),
    metric('Unseen transfer · after teaching',r.transfer.correct+'/'+r.transfer.total),
    metric('Additional retest',r.retest.total ? r.retest.correct+'/'+r.retest.total : 'Not needed'));
  content.append(stats);
  append(content,paragraph('Confidence calibration (descriptive Brier score): '+r.calibrationBrierDescriptive+'. Lower is better, but a short three-item assessment is not a validated mastery measure.'));
  append(content,notice('Mastery: UNKNOWN · causal learning improvement: UNKNOWN · independent evaluator: NOT CONNECTED. These results prove only how this local session answered a small set of items.'));
  append(content,heading('Explain the principle in your own words'),paragraph('What would have to be true to rebuild a changing system after disconnecting it? What could still make reconstruction impossible?'));
  const t=node('textarea','reflect');t.setAttribute('aria-label','Private learner reflection');t.placeholder='Explain the dependencies and limits without mentioning gardens, seeds or music. No automatic grading; your words remain in this tab.';
  append(content,t,paragraph('This reflection is not sent, saved or automatically judged. For an actual research study it needs a consented independent evaluator and a held-out rubric.','note'));
  append(content,append(node('div','actions'),
    makeButton('Export anonymous local results',()=>{
      const payload=JSON.stringify({version:PILOT_VERSION,report:r,recordedAt:null,consentedResearchSubmission:false},null,2);
      const blob=new Blob([payload],{type:'application/json'});const url=URL.createObjectURL(blob);
      const a=node('a');a.href=url;a.download='triad-local-research-observation.json';a.click();
      setTimeout(()=>URL.revokeObjectURL(url),1000);
    }),
    makeButton('Restart local pilot',()=>{session=startSession({arm:$('arm').value});render();},'secondary')
  ));
}
function render() {
  content.replaceChildren();
  progress();
  const v=currentView(session);
  if(v.question)renderQuestion(v);
  else if(v.phase==='teach')teach(v);
  else if(v.phase==='remediation')remedy(v);
  else if(v.phase==='complete')result();
  else append(content,notice('The research session is in an unsupported state. No learning result can be claimed.'));
}
$('arm').addEventListener('change',evt=>{
  // This is a learner-chosen demonstration, NOT randomised causal allocation.
  session=startSession({arm:evt.target.value});
  render();
});
render();
