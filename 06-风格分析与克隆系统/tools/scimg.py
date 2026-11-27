"""SC-IMG 1.0.0: offline structural validation, deterministic export and review gates.
No model calls, image interpretation or translation. Python 3.10+ standard library.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = {
    'subject_kind': ['human','animal','object','architecture','landscape','abstract','mixed'],
    'scene_kind': ['interior','exterior','studio','none','mixed'],
    'shot_type': ['close','medium','wide','flat'],
    'text_mode': ['required','forbidden','optional'],
}
LABELS = {
 'subject_kind':'主体类型','scene_kind':'场景类型','shot_type':'景别','text_mode':'文字要求',
 'human':'人物','animal':'动物','object':'物品','architecture':'建筑','landscape':'风景','abstract':'抽象','mixed':'混合',
 'interior':'室内','exterior':'室外','studio':'摄影棚','none':'无场景','close':'近景','medium':'中景','wide':'远景','flat':'平面',
 'required':'需要文字','forbidden':'禁止文字','optional':'文字可选',
}

def _pairs(pairs):
    out = {}
    for k,v in pairs:
        if k in out: raise ValueError('Duplicate JSON key: '+k)
        out[k] = v
    return out

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=_pairs,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError('Non-finite JSON: '+s)))

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()

def schema_errors(value, schema, path='$'):
    """Checks the subset used by the shipped schemas; not a general JSON Schema engine."""
    errors=[]
    types={'object':lambda x:isinstance(x,dict),'array':lambda x:isinstance(x,list),
           'string':lambda x:isinstance(x,str),'boolean':lambda x:isinstance(x,bool),
           'null':lambda x:x is None,'number':lambda x:isinstance(x,(int,float)) and not isinstance(x,bool)}
    ts=schema.get('type');ts=[ts] if isinstance(ts,str) else ts
    if ts and not any(types[t](value) for t in ts):return [path+': invalid type']
    if 'const' in schema and value!=schema['const']:errors.append(path+': wrong version/constant')
    if 'enum' in schema and value not in schema['enum']:errors.append(path+': value outside enum')
    if isinstance(value,str):
        if len(value)<schema.get('minLength',0) or ('minLength' in schema and not value.strip()):errors.append(path+': empty string')
        if 'pattern' in schema and re.search(schema['pattern'],value) is None:errors.append(path+': pattern mismatch')
    if isinstance(value,dict):
        for k in schema.get('required',[]):
            if k not in value:errors.append(path+'.'+k+': missing')
        for k,v in value.items():
            if k in schema.get('properties',{}):errors+=schema_errors(v,schema['properties'][k],path+'.'+k)
            elif schema.get('additionalProperties') is False:errors.append(path+'.'+k+': unknown field')
    if isinstance(value,list):
        if len(value)<schema.get('minItems',0):errors.append(path+': too few items')
        if schema.get('uniqueItems') and len({digest(v) for v in value})!=len(value):errors.append(path+': repeated item')
        for i,v in enumerate(value):errors+=schema_errors(v,schema.get('items',{}),path+f'[{i}]')
    return errors

def condition(when, context):
    unknown=False
    for k,allowed in when.items():
        v=context[k]
        if v=='unknown':unknown=True
        elif v not in allowed:return False
    return None if unknown else True

def possible_together(a,b):
    return all(set(a.get(k,vals)) & set(b.get(k,vals)) for k,vals in CONTEXT.items())

def implies(a,b):
    return all(set(a.get(k,vals)) <= set(b.get(k,vals)) for k,vals in CONTEXT.items())

def analyze(bundle):
    errors=schema_errors(bundle,load(ROOT/'schemas/bundle.schema.json'))
    result={'errors':errors,'pending':[],'warnings':[],'active':[],'inactive':[],'unknown':[]}
    if errors:return result
    p=bundle['profile'];task=bundle['task'];rules=p['rules'];index={r['id']:r for r in rules}
    refs={r['id']:r for r in p['references']};ev={e['id']:e for e in p['evidence']}
    for label,rows in [('rules',rules),('references',p['references']),('evidence',p['evidence']),('requirements',task['requirements'])]:
        if len({r['id'] for r in rows})!=len(rows):errors.append(label+': duplicate IDs')
    if {r['id'] for r in rules}&{r['id'] for r in task['requirements']}:errors.append('Style and task IDs must not collide')
    if not any(r['scope']=='core' for r in rules):errors.append('No core rules; extract a style before compiling')
    for e in ev.values():
        if e['reference_id'] not in refs:errors.append(e['id']+': missing reference')
        elif e['provenance']=='observed' and not refs[e['reference_id']]['seen']:errors.append(e['id']+': cannot claim observation of an unseen reference')
        if e['provenance']=='illustrative' and not p['illustrative']:errors.append(e['id']+': illustrative evidence requires illustrative profile')
    for r in rules:
        if not r['id'].startswith('R'):errors.append(r['id']+': style IDs must start with R')
        if r['scope']=='core' and (r['when'] or r['priority']!='must'):errors.append(r['id']+': core must be unconditional and must')
        if r['scope']=='conditional' and not r['when']:errors.append(r['id']+': conditional rule needs conditions')
        if p['dimensions'][r['dimension']]['state']!='active':errors.append(r['id']+': rule dimension must be active')
        for eid in r['evidence_ids']:
            if eid not in ev:errors.append(r['id']+': unknown evidence '+eid)
        for other in r['requires']+r['excludes']:
            if other not in index:errors.append(r['id']+': unknown related rule '+other)
            if other==r['id']:errors.append(r['id']+': self dependency/exclusion')
    for t in task['requirements']:
        if not t['id'].startswith('T'):errors.append(t['id']+': task IDs must start with T')
        for rid in t['conflicts_with']:
            if rid not in index:errors.append(t['id']+': unknown conflict target '+rid)
    visiting=set();visited=set()
    def visit(rid):
        if rid in visiting:errors.append('Dependency cycle at '+rid);return
        if rid in visited or rid not in index:return
        visiting.add(rid)
        for other in index[rid]['requires']:visit(other)
        visiting.remove(rid);visited.add(rid)
    for rid in index:visit(rid)
    for r in rules:
        state=True if task['mode']=='template' else condition(r['when'],task['context'])
        result['unknown' if state is None else 'active' if state else 'inactive'].append(r['id'])
    active=set(result['active'])
    for r in rules:
        if r['id'] not in active:continue
        for dep in r['requires']:
            if dep in index and (dep not in active or (task['mode']=='template' and not implies(r['when'],index[dep]['when']))):
                errors.append(r['id']+': dependency not guaranteed: '+dep)
        for ex in r['excludes']:
            if ex in active and (task['mode']!='template' or possible_together(r['when'],index[ex]['when'])):errors.append(r['id']+': excludes active rule '+ex)
        if r['disposition']=='candidate':result['pending'].append(r['id']+': candidate rule is not confirmed')
    for t in task['requirements']:
        if active.intersection(t['conflicts_with']):errors.append(t['id']+': conflicts with active style')
    if task['mode']=='instance' and any('{{' in task['content'][l] for l in ('zh','en')):errors.append('Instance contains unfilled placeholders')
    if task['context']['text_mode']=='unknown' and task['mode']=='instance':result['warnings'].append('Text requirement unspecified')
    result['pending']+=p['unresolved']+task['unresolved']+[rid+': condition unknown' for rid in result['unknown']]
    if p['illustrative']:result['pending'].append('ILLUSTRATIVE: invented test data, not image extraction')
    if p['status']=='draft':result['pending'].append('Profile remains draft')
    if p['status']=='validated':
        if p['illustrative'] or not any(v['result']=='pass' for v in p['validation_records']):errors.append('Validated profile needs non-illustrative pass records')
        if any(r['disposition']!='confirmed' for r in rules if r['scope']=='core'):errors.append('Validated core contains candidates')
    result['warnings']+=['Bilingual semantic equivalence requires review; structural checks do not prove it.',
                        'Image fidelity is not evaluated by this tool.']
    return result

def localized_condition(when, lang):
    if not when:return ''
    if lang=='zh':return '当'+ '且'.join(LABELS[k]+'为'+ '/'.join(LABELS[v] for v in vs) for k,vs in when.items())+'时：'
    return 'When '+ ' and '.join(k+' is '+ ' or '.join(vs) for k,vs in when.items())+': '

def compile_bundle(bundle, draft=False):
    state=analyze(bundle)
    if state['errors']:raise ValueError('\n'.join(state['errors']))
    if state['pending'] and not draft:raise ValueError('Unresolved state; inspect check output, or explicitly export a draft: '+'; '.join(state['pending']))
    p=bundle['profile'];task=bundle['task'];status='draft' if state['pending'] else task['mode']=='template' and 'template' or 'ready'
    included=set(state['active']+state['unknown'])
    rules=sorted((r for r in p['rules'] if r['id'] in included),key=lambda r:(r['scope']!='core',{'must':0,'should':1,'may':2}[r['priority']],r['id']))
    metadata={'system_version':bundle['system_version'],'schema_version':bundle['schema_version'],'profile_id':p['id'],
              'profile_version':p['version'],'task_id':task['id'],'task_mode':task['mode'],'source_digest':digest(bundle),
              'export_status':status,'illustrative':p['illustrative'],'image_status':'not_generated',
              'semantic_equivalence':'not_checked','pending':state['pending']}
    files={};localized={}
    for lang in ('zh','en'):
        rows=[{'id':r['id'],'scope':r['scope'],'priority':r['priority'],'when':r['when'],'instruction':r['instruction'][lang],
               'variation':r['variation'][lang],'check':r['check'][lang]} for r in rules]
        reqs=[{'id':t['id'],'priority':t['priority'],'instruction':t['instruction'][lang],'check':t['check'][lang]} for t in task['requirements']]
        localized[lang]={'metadata':metadata,'language':lang,'content':task['content'][lang],'context':task['context'],'style_rules':rows,'task_requirements':reqs}
    files['01_prompt_zh.json']=json.dumps(localized['zh'],ensure_ascii=False,indent=2)+'\n'
    files['02_prompt_en.json']=json.dumps(localized['en'],ensure_ascii=False,indent=2)+'\n'
    for lang,name in [('zh','03_prompt_zh_simple.txt'),('en','04_prompt_en_natural.txt')]:
        head=(f'SC-IMG {p["id"]}@{p["version"]} | {status} | {digest(bundle)}\n')
        notice=('【自拟演示；不是风格提取结果】' if lang=='zh' else '[ILLUSTRATIVE TEST DATA; NOT AN EXTRACTED STYLE]') if p['illustrative'] else ''
        pending=('【草案；存在未决项，尚未验证成图】' if lang=='zh' else '[DRAFT; UNRESOLVED ITEMS; NO IMAGE VALIDATION]') if status=='draft' else ('【提示词方案；成图尚未验证】' if lang=='zh' else '[PROMPT SPECIFICATION; IMAGE NOT YET VALIDATED]')
        lines=[head,notice,pending,task['content'][lang]]
        for r in rules:
            priority={'must':'必须','should':'建议','may':'可选'}[r['priority']] if lang=='zh' else r['priority'].upper()
            lines.append(f'[{r["id"]}] {localized_condition(r["when"],lang)}{priority}：{r["instruction"][lang]} '+r['variation'][lang])
        for t in task['requirements']:
            priority={'must':'必须','should':'建议','may':'可选'}[t['priority']] if lang=='zh' else t['priority'].upper()
            lines.append(f'[{t["id"]}] {priority}：{t["instruction"][lang]}')
        if state['pending']:lines.append(('未决事项：' if lang=='zh' else 'Unresolved items: ')+'; '.join(state['pending']))
        files[name]='\n'.join(x for x in lines if x)+'\n'
    coverage={**metadata,'active_rule_ids':state['active'],'inactive_rule_ids':state['inactive'],'unknown_rule_ids':state['unknown'],
              'coverage':{name:{'style_rules':[r['id'] for r in rules],'task_requirements':[t['id'] for t in task['requirements']]} for name in files},
              'reuse':'Edit task and recompile. Do not silently alter core rules.', 'warnings':state['warnings']}
    files['coverage.json']=json.dumps(coverage,ensure_ascii=False,indent=2)+'\n'
    return files

def audit_review(bundle, review):
    state=analyze(bundle);errors=state['errors']+schema_errors(review,load(ROOT/'schemas/review.schema.json'))
    if errors:raise ValueError('\n'.join(errors))
    if review['source_digest']!=digest(bundle):raise ValueError('Review belongs to a different bundle/version')
    if bundle['task']['mode']!='instance':raise ValueError('Review needs a concrete task instance')
    if review['image_status']!='reviewed':
        if review['checks']:raise ValueError('Unreviewed image cannot contain completed checks')
        return {'result':'unknown','image_status':review['image_status'],'reason':'No actual image review is available'}
    if not review['image_ref'] or not review['image_ref'].strip():raise ValueError('Reviewed image needs an image reference')
    rows=review['checks'];checks={r['id']:r for r in rows}
    if len(checks)!=len(rows):raise ValueError('Duplicate review IDs')
    applicable=[r for r in bundle['profile']['rules'] if r['id'] in state['active']]+bundle['task']['requirements']
    ids={r['id'] for r in applicable}
    if set(checks)-ids:raise ValueError('Review contains unknown/inactive IDs')
    must={r['id'] for r in applicable if r['priority']=='must'}
    failed=sorted(i for i in must if i in checks and checks[i]['result']=='fail')
    unknown=sorted(i for i in must if i not in checks or checks[i]['result'] not in ('pass','fail'))
    uncertain=bool(state['pending']) or bundle['profile']['illustrative']
    result='fail' if failed else 'unknown' if unknown or uncertain else 'pass'
    return {'result':result,'failed_must':failed,'unknown_must':unknown,'pending':state['pending'],
            'non_must_findings':[r for r in rows if r['id'] not in must and r['result']!='pass'],
            'evidence_verification':'Record completeness checked only; actual pixels and statements require visual review.'}

def verify_package(folder):
    root=Path(folder).resolve();manifest=load(root/'manifest.json');bad=[]
    for name,expected in manifest['files'].items():
        p=(root/name).resolve()
        if not p.is_relative_to(root):raise ValueError('Manifest path escapes package')
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:bad.append(name)
    if bad:raise ValueError('Missing or changed package files: '+', '.join(bad))
    return {'integrity':'verified','files':len(manifest['files']),'authenticity':'not_established_by_hash'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='cmd',required=True)
    c=sub.add_parser('check');c.add_argument('bundle')
    c=sub.add_parser('compile');c.add_argument('bundle');c.add_argument('--out',required=True);c.add_argument('--draft',action='store_true')
    c=sub.add_parser('review');c.add_argument('bundle');c.add_argument('review')
    c=sub.add_parser('verify-package');c.add_argument('folder')
    args=parser.parse_args()
    try:
        if args.cmd=='verify-package':answer=verify_package(args.folder)
        elif args.cmd=='check':
            answer=analyze(load(args.bundle));print(json.dumps(answer,ensure_ascii=False,indent=2));return 1 if answer['errors'] else 0
        elif args.cmd=='review':answer=audit_review(load(args.bundle),load(args.review))
        else:
            files=compile_bundle(load(args.bundle),args.draft);out=Path(args.out)
            if out.exists() and (not out.is_dir() or any(out.iterdir())):raise ValueError('Output must be a new or empty directory; existing files are not overwritten')
            out.mkdir(parents=True,exist_ok=True)
            for name,text in files.items():(out/name).write_text(text,encoding='utf-8')
            answer={'files':[str(out/name) for name in files],'status':json.loads(files['coverage.json'])['export_status']}
        print(json.dumps(answer,ensure_ascii=False,indent=2));return 0
    except (ValueError,OSError,KeyError,TypeError) as ex:
        print('ERROR: '+str(ex),file=sys.stderr);return 1

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
