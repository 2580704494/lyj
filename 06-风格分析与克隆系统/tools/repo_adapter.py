"""LYJ handoff 1.0: map explicit repository constraints to a new SC-IMG task.
No vision, translation, automatic semantic conflict discovery or generation.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path, PurePosixPath
import sys

import scimg

ROOT = Path(__file__).resolve().parents[1]
MODULES = {
    '01': '01-信息图形数据逻辑', '02': '02-信息图形类型案例',
    '03': '03-ISOTYPE信息图', '04': '04-统计图形分析',
    '05': '05-Gestalt视觉组织原则',
}


def check_source(source, module, repo_root):
    path = PurePosixPath(source)
    if ('\\' in source or ':' in source or path.is_absolute() or '..' in path.parts
            or not path.parts or path.parts[0] != MODULES[module]):
        raise ValueError('Invalid source path for module ' + module + ': ' + source)
    base = Path(repo_root).resolve()
    target = (base / source).resolve()
    if not target.is_relative_to(base) or not target.is_file():
        raise ValueError('Repository source missing or outside root: ' + source)


def merge(handoff, bundle, repo_root):
    errors = scimg.schema_errors(handoff, scimg.load(ROOT / 'schemas/repo_handoff.schema.json'))
    errors += scimg.analyze(bundle)['errors']
    if errors:
        raise ValueError('; '.join(errors))
    modules = {m['id']: m for m in handoff['modules']}
    if len(modules) != len(handoff['modules']):
        raise ValueError('Duplicate module ID')
    for module in modules.values():
        check_source(module['source'], module['id'], repo_root)
    result = deepcopy(bundle)
    # Replace the entire task: preserving old task locks would leak old subjects.
    result['task'] = deepcopy(handoff['task'])
    mapping = []
    for constraint in handoff['constraints']:
        if constraint['module'] not in modules:
            raise ValueError('Constraint uses undeclared module: ' + constraint['module'])
        check_source(constraint['source'], constraint['module'], repo_root)
        result['task']['requirements'].append({
            k: deepcopy(constraint[k]) for k in
            ('id', 'priority', 'instruction', 'check', 'conflicts_with')
        })
        mapping.append({k: constraint[k] for k in ('id', 'module', 'source')})
    result['task']['unresolved'].extend(handoff['unresolved'])
    state = scimg.analyze(result)
    if state['errors']:
        raise ValueError('; '.join(state['errors']))
    trace = {
        'handoff_version': '1.0', 'input_bundle_digest': scimg.digest(bundle),
        'handoff_digest': scimg.digest(handoff), 'output_bundle_digest': scimg.digest(result),
        'profile_id': bundle['profile']['id'], 'profile_version': bundle['profile']['version'],
        'profile_unchanged': result['profile'] == bundle['profile'],
        'task_replaced': True, 'modules': deepcopy(handoff['modules']),
        'constraints': mapping, 'pending': state['pending'],
        'limitations': ['Explicit constraints only; no semantic conflict discovery.',
                        'No images generated or visually reviewed.'],
    }
    return result, trace


def write_output(folder, handoff, bundle, trace):
    folder = Path(folder)
    if folder.exists() and (not folder.is_dir() or any(folder.iterdir())):
        raise ValueError('Output must be a new or empty directory')
    folder.mkdir(parents=True, exist_ok=True)
    for name, value in [('bundle.json', bundle), ('handoff.json', handoff), ('trace.json', trace)]:
        with (folder / name).open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('handoff')
    parser.add_argument('bundle')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    try:
        handoff = scimg.load(args.handoff)
        bundle, trace = merge(handoff, scimg.load(args.bundle), ROOT.parent)
        write_output(args.out, handoff, bundle, trace)
        print(json.dumps({'written': args.out, 'profile_unchanged': True,
                          'pending': trace['pending']}, ensure_ascii=False))
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
