"""Deterministic adapters to archived, finite-profile abstract research kernels."""
from __future__ import annotations
from importlib.resources import files
from pathlib import Path
import hashlib
import math
import platform
import sys
import numpy as np
from .language import CircleError, VERSION, load_artifact, digest, canonical


def data(name):
    import json
    return json.loads(files('circle_lang').joinpath('data', name).read_text(encoding='utf-8'))


def _number(x, name, low=0., high=float('inf'), strict=False):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise CircleError(f'{name} must be finite numeric data')
    if x > high or (x <= low if strict else x < low): raise CircleError(f'{name} is out of range')
    return float(x)


def _choose(rows, key, name):
    found = next((x for x in rows if x[key] == name), None)
    if found is None: raise CircleError(f'unknown scenario {name!r}; available: {", ".join(x[key] for x in rows)}')
    return found.copy()


def resolve_config(p, config):
    if config is None: config = {}
    if not isinstance(config, dict): raise CircleError('configuration must be a JSON object')
    allowed = {
        'logic': {'signals'}, 'navigation': {'world', 'fields', 'noise'},
        'homeostasis': {'scenario', 'context'},
        'composition': {'world', 'fields', 'noise', 'disturbance'},
        'cohesion': {'geometry', 'noise', 'interaction'},
    }[p.profile]
    if set(config) - allowed: raise CircleError(f'unsupported {p.profile} configuration keys: {sorted(set(config)-allowed)}')
    if p.profile == 'logic':
        signals = config.get('signals', {})
        if not isinstance(signals, dict) or set(signals) - set(p.inputs): raise CircleError('signals must map declared inputs to HIGH or LOW')
        if any(x not in ['HIGH', 'LOW'] for x in signals.values()): raise CircleError('signal values must be HIGH or LOW')
        return {'signals': {name: signals.get(name, 'LOW') for name in p.inputs}}
    if p.profile in {'navigation', 'composition'}:
        nav = p.profile == 'navigation'
        worlds = data('navigation_worlds.json' if nav else 'composition_worlds.json')['worlds']
        w = _choose(worlds, 'id', config.get('world', worlds[0]['id']))
        max_coord = 1 if nav else 100
        noise_key = 'random_motion_rms_per_tick' if nav else 'noise'
        if 'fields' in config:
            if 'world' in config: raise CircleError('choose either world or fields')
            f = config['fields']
            if not isinstance(f, dict) or set(f) != {p.toward, p.avoid}: raise CircleError('fields must bind both source input names')
            for name, dest in [(p.toward, 'A'), (p.avoid, 'B')]:
                xyz = f[name]
                if not isinstance(xyz, list) or len(xyz) != 3: raise CircleError('each field is [center_x, center_y, sigma]')
                w[dest] = [_number(xyz[0],name,high=max_coord), _number(xyz[1],name,high=max_coord), _number(xyz[2],name,strict=True)]
            w['id'] = 'custom'; w['stratum'] = 'user_defined'
        w[noise_key] = _number(config.get('noise', w[noise_key]), 'noise', high=max_coord)
        out = {'world': w, 'bindings': {p.toward: 'A', p.avoid: 'B'}, 'domain': [0,max_coord], 'cells':64, 'steps':190 if nav else 200}
        if not nav:
            rows = data('composition_disturbances.json')['disturbances']
            out['disturbance'] = _choose(rows, 'id', config.get('disturbance', rows[0]['id']))
        return out
    if p.profile == 'homeostasis':
        from ._research.runtime_m62 import SCENARIOS
        scenario = config.get('scenario', SCENARIOS[0].name)
        if scenario not in [s.name for s in SCENARIOS]: raise CircleError('unknown homeostasis scenario')
        context = {'state_sensor_gain':1., 'state_sensor_offset':0., 'actuator_efficiency':1., 'disturbance_multiplier':1., 'noise_multiplier':1.}
        requested = config.get('context', {})
        if not isinstance(requested, dict) or set(requested)-set(context): raise CircleError('unknown homeostasis context key')
        context.update(requested)
        for k, v in context.items():
            context[k] = _number(v,k,low=-float('inf') if k=='state_sensor_offset' else 0, strict=k!='state_sensor_offset')
        return {'scenario':scenario,'context':context,'cells':64,'steps':200,'domain':[0,1]}
    geometry = config.get('geometry', 'uniform_cloud')
    if geometry not in ['uniform_cloud','bimodal_horizontal','bimodal_diagonal','ring','boundary_biased']:
        raise CircleError('unsupported cohesion geometry')
    interaction = config.get('interaction', True)
    if type(interaction) is not bool: raise CircleError('interaction must be true or false')
    return {'geometry':geometry,'noise':_number(config.get('noise',.01),'noise',high=1),
            'interaction':interaction,'cells':64,'steps':220,'domain':[0,1]}


def _logic(p, signals):
    state = {key:'INACTIVE' for key in p.states}
    trace = [{'tick':0, 'states':state.copy()}]
    def matches(rule, snapshot):
        return all((signals if c.name in signals else snapshot)[c.name] == c.value for c in rule.conditions)
    for iteration in range(1,33):
        proposals = {}
        for rule in p.rules:
            if matches(rule, state):
                for action in rule.actions:
                    if action.verb in {'activate','deactivate'}:
                        proposals.setdefault(action.target,set()).add('ACTIVE' if action.verb=='activate' else 'INACTIVE')
        if any(len(v)>1 for v in proposals.values()): raise CircleError('conflicting synchronous state transitions')
        updated = {**state, **{key:next(iter(v)) for key,v in proposals.items()}}
        trace.append({'tick':iteration, 'states':updated.copy()})
        if updated == state: break
        state = updated
    else: raise CircleError('logical state did not converge within 32 rounds')
    phenotype = {'motility':1.,'division':1.,'secretion':0.}
    for rule in p.rules:
        if matches(rule,state):
            for a in rule.actions:
                if a.verb in {'increase','decrease'}:
                    if a.target == 'secretion': phenotype[a.target] = 1. if a.verb=='increase' else 0.
                    else: phenotype[a.target] *= 2. if a.verb=='increase' else .5
    return phenotype, state, trace


def check_contract(p, metrics):
    tests = []
    for c in p.constraints:
        x = metrics[c.metric]
        passed = x >= c.value if c.op == '>=' else x <= c.value if c.op == '<=' else x == c.value
        tests.append({'metric':c.metric,'actual':x,'op':c.op,'threshold':c.value,'passed':bool(passed)})
    return tests, all(t['passed'] for t in tests) if tests else None


def run(artifact: dict, *, config=None, seeds=(0,), trace=True) -> dict:
    """Execute validated BioIR. Source contracts apply separately to each run.

    Trace, when enabled, stores all ticks for the first seed only.
    Passing contracts is empirical evidence, never a certification.
    """
    p = load_artifact(artifact)
    seeds = list(seeds)
    if not seeds or any(type(s) is not int or not 0 <= s <= 2**32-1 for s in seeds): raise CircleError('seeds must be nonempty integers in [0, 2^32-1]')
    if len(set(seeds)) != len(seeds): raise CircleError('duplicate seeds would duplicate evidence')
    if type(trace) is not bool: raise CircleError('trace must be boolean')
    resolved = resolve_config(p, config)
    frames = []; rows = []
    def observer(tick, positions=None, state=None):
        frame = {'tick':int(tick)}
        if positions is not None: frame['positions'] = positions.tolist()
        if state is not None: frame['state'] = state.tolist()
        frames.append(frame)
    if p.profile == 'composition':
        from ._research.benchmark_m718 import run_pair
        obs = (lambda t,x,h: observer(t,x[0],h[0])) if trace else None
        raw_rows = run_pair('viability_debt_linker_v3',resolved['world'],resolved['disturbance'],seeds,observer=obs)
        for row in raw_rows:
            row['research_task_pass'] = bool(row.pop('joint_pass'))
            rows.append(row)
    else:
        for i, seed in enumerate(seeds):
            obs = observer if trace and i == 0 else None
            if p.profile == 'logic':
                metrics, state, logic_trace = _logic(p,resolved['signals'])
                row = {**metrics,'final_states':state}
                if obs: frames.extend(logic_trace)
            elif p.profile == 'navigation':
                from ._research.navigation import runA
                row = runA(resolved['world'],seed,observer=obs)
                row['research_task_pass'] = row.pop('task_pass')
            elif p.profile == 'homeostasis':
                from ._research.bioir_m6 import HomeostasisBioIR, IRContinuousState, IRHomeostasis
                from ._research.compiler_m62 import compile_for_runtime, HomeostasisRuntimeContext
                from ._research.runtime_m62 import run_one, SCENARIOS
                ir = HomeostasisBioIR(p.name,IRContinuousState(p.continuous,0,1),IRHomeostasis(p.continuous,*p.interval),())
                ctx = HomeostasisRuntimeContext('circle',**resolved['context'])
                program = compile_for_runtime(ir,ctx,mode='recompiled_v1')
                scenario = next(s for s in SCENARIOS if s.name == resolved['scenario'])
                row = run_one(program,scenario,seed,observer=(lambda t,h: obs(t,state=h)) if obs else None)
                row['research_task_pass'] = bool(row.pop('passed'))
                row['trigger_interval'] = [program.trigger_low_canonical,program.trigger_high_canonical]
            else:
                from ._research.cohesion import init_positions,random_units,core,metrics as cohesion_metrics
                rng = np.random.default_rng(seed); positions = init_positions(resolved['geometry'],rng)
                positions = core(positions,random_units(rng),resolved['interaction'],resolved['noise'],observer=obs)
                g,r,o = cohesion_metrics(positions)
                row = {'giant_component_fraction':g,'radius_of_gyration':r,'overcrowding_fraction':o,
                       'research_task_pass':bool(g>=.85 and r<=.18 and o<=.1)}
            row['seed'] = seed; rows.append(row)
    for row in rows:
        checks, passed = check_contract(p,row)
        row['contract_checks'] = checks; row['contract_pass'] = passed
    all_pass = all(r['contract_pass'] for r in rows) if p.constraints else None
    provenance = data('provenance.json')
    package = Path(__file__).parent
    implementation = {str(f.relative_to(package)):hashlib.sha256(f.read_bytes()).hexdigest()
                      for f in sorted(package.rglob('*.py'))}
    report = {'schema':'circle.run.v1','circle_version':VERSION,'program':p.name,'profile':p.profile,
              'kernel':artifact['kernel'],'backend':'abstract-cpu','artifact_sha256':digest(artifact),
              'source_sha256':artifact['source_sha256'],'source':artifact['source'],
              'behavior_specification':artifact['program'],'configuration':resolved,'configuration_sha256':digest(resolved),
              'provenance_sha256':digest(provenance),'implementation_sha256':digest(implementation),'seeds':seeds,'certification':'not_certified',
              'evidence':'local_execution; observed scenarios; not a blind study',
              'environment':{'python':sys.version.split()[0],'numpy':np.__version__,'platform':platform.platform()},
              'summary':{'run_count':len(rows),'contract_pass_count':sum(r['contract_pass'] is True for r in rows),
                         'all_contracts_pass':all_pass,'contract_scope':'each_run'},
              'runs':rows,'trace':{'seed':seeds[0] if trace else None,'frames':frames}}
    canonical(report)  # Reject accidental NaN/Infinity before returning evidence.
    return report
