import {test} from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const ROOT = fileURLToPath(new URL('../../../../', import.meta.url));
const PROBE = String.raw`
import importlib.machinery, importlib.util, json, sys, tomllib
from pathlib import Path
root=Path(sys.argv[1])
registry=root/'platform/llm/pennyd/providers'
for name in ('gemini','groq','openrouter'):
    spec=tomllib.loads((registry/(name+'.toml')).read_text())
    assert spec['id']==name, name
    assert spec['dialect']=='openai', name
    assert isinstance(spec.get('models'), list), name+': models missing at the root'
    assert 'models' not in spec.get('auth',{}), name+': models accidentally nested in auth'
loader=importlib.machinery.SourceFileLoader('legion_admit_provider_census',str(root/'bin/legion-admit'))
module_spec=importlib.util.spec_from_loader(loader.name,loader)
module=importlib.util.module_from_spec(module_spec)
loader.exec_module(module)
env={'GEMINI_API_KEY':'synthetic-only','GROQ_API_KEY':'synthetic-only','OPENROUTER_API_KEY':'synthetic-only'}
selected={route['provider'] for route in module.auto_candidates(registry,env)}
assert 'gemini' not in selected, selected
assert {'groq','openrouter'}<=selected, selected
print(json.dumps({'gemini_disabled':True,'alternates':sorted(selected),'capacity_probed':False}))
`;

test('malformed Gemini declaration cannot blind the real Legion provider census', () => {
  const result=spawnSync('python3',['-c',PROBE,ROOT],{encoding:'utf8',timeout:12000});
  assert.equal(result.error,undefined,String(result.error));
  assert.equal(result.status,0,`No live API calls intended: ${result.stderr}`);
  const receipt=JSON.parse(result.stdout);
  assert.equal(receipt.gemini_disabled,true);
  assert.equal(receipt.capacity_probed,false);
  assert.ok(receipt.alternates.includes('groq'));
  assert.ok(receipt.alternates.includes('openrouter'));
});
