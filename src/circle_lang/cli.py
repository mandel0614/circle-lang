"""Command-line interface. No source or artifact code is evaluated as Python."""
import argparse
import json
from pathlib import Path
import sys
from .language import CircleError, VERSION, compile_source, load_artifact
from .runtime import run, data
from .report import render_report


def read_json(path):
    def unique(pairs):
        result = {}
        for key,value in pairs:
            if key in result: raise CircleError(f'duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(CircleError(f'invalid JSON number {x}')))


def read_program(path):
    if Path(path).suffix == '.json':
        a = read_json(path); load_artifact(a); return a
    return compile_source(Path(path).read_text(encoding='utf-8'))


def write_json(path, obj):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def seed_list(value):
    try:
        if ':' in value:
            start,stop = map(int,value.split(':'))
            if not 1 <= stop-start <= 10000: raise ValueError('range must contain 1 to 10000 seeds')
            result = list(range(start,stop))
        else: result = [int(x) for x in value.split(',')]
    except ValueError: raise argparse.ArgumentTypeError('use 0,1,2 or 0:10 (exclusive stop)')
    if not result or len(result)>10000: raise argparse.ArgumentTypeError('choose 1 to 10000 seeds')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(prog='circle',description='Circle for virtual cell programming — abstract CPU research preview')
    parser.add_argument('--version',action='version',version=VERSION)
    commands = parser.add_subparsers(dest='command',required=True)
    for name in ['check','compile','run','verify']:
        p = commands.add_parser(name); p.add_argument('source',help='.circle source or compiled .json BioIR')
        if name == 'compile': p.add_argument('-o','--output',required=True)
        if name in {'run','verify'}:
            p.add_argument('--config',help='JSON scenario and runtime bindings')
            p.add_argument('--seeds',type=seed_list,default=[0],help='comma list or start:stop (exclusive)')
            p.add_argument('-o','--output',default='runs/latest.json')
            p.add_argument('--html',help='optional self-contained trajectory report')
            p.add_argument('--no-trace',action='store_true')
    commands.add_parser('scenarios',help='list bundled observed scenarios')
    args = parser.parse_args(argv)
    try:
        if args.command == 'scenarios':
            from ._research.runtime_m62 import SCENARIOS
            print(json.dumps({'navigation':[w['id'] for w in data('navigation_worlds.json')['worlds']],
                              'composition_worlds':[w['id'] for w in data('composition_worlds.json')['worlds']],
                              'composition_disturbances':[d['id'] for d in data('composition_disturbances.json')['disturbances']],
                              'homeostasis':[s.name for s in SCENARIOS],
                              'cohesion':['uniform_cloud','bimodal_horizontal','bimodal_diagonal','ring','boundary_biased']},indent=2)); return 0
        artifact = read_program(args.source)
        inputs = {Path(args.source).resolve()}
        if getattr(args, 'config', None): inputs.add(Path(args.config).resolve())
        outputs = [Path(x).resolve() for x in [getattr(args,'output',None),getattr(args,'html',None)] if x]
        if inputs.intersection(outputs) or len(outputs) != len(set(outputs)):
            raise CircleError('input, output, and HTML paths must be distinct')
        if args.command == 'check':
            print(f"Valid: {artifact['program']['name']} / {artifact['program']['profile']} / {artifact['kernel']}"); return 0
        if args.command == 'compile':
            write_json(args.output,artifact); print(f'Compiled BioIR: {args.output}'); return 0
        if args.command == 'verify' and not artifact['program']['constraints']:
            raise CircleError('verify requires at least one source contract')
        report = run(artifact,config=read_json(args.config) if args.config else None,seeds=args.seeds,trace=not args.no_trace)
        write_json(args.output,report)
        if args.html:
            Path(args.html).parent.mkdir(parents=True,exist_ok=True)
            Path(args.html).write_text(render_report(report),encoding='utf-8')
        print(json.dumps(report['summary'],indent=2)); print(f'Run receipt: {args.output}; certification: not_certified')
        return 1 if args.command == 'verify' and not report['summary']['all_contracts_pass'] else 0
    except (CircleError,OSError,ValueError,TypeError,KeyError) as e:
        print(f'circle: {e}',file=sys.stderr); return 2

if __name__ == '__main__': sys.exit(main())
