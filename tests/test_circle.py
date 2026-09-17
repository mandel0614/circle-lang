import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import hashlib
import numpy as np
from circle_lang import CircleError, compile_source, parse, run
from circle_lang.language import load_artifact, canonical
from circle_lang.cli import main, read_json, seed_list
from circle_lang.runtime import data
from circle_lang.report import render_report

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT/'tests/fixtures'
def example(n): return next((ROOT/'examples').glob(n+'*.circle')).read_text()
def fixture(name): return json.loads((FIX/name).read_text())

class LanguageTests(unittest.TestCase):
    def test_profiles(self):
        for prefix,profile in [('00','logic'),('01','navigation'),('02','homeostasis'),('03','composition'),('04','cohesion')]:
            with self.subTest(profile=profile):
                a=compile_source(example(prefix));self.assertEqual(load_artifact(a).profile,profile)

    def test_invalid_sources(self):
        cases = ['', 'cell C {}', 'cell C { cohere; } trailing', 'cell C { cohere; mystery; }',
                 'cell C { cohere; cohere; }', 'cell C { input A; input A; }',
                 'cell C { input A; migrate toward A; }',
                 'cell C { input A; avoid A; migrate toward A; }',
                 'cell C { state H in [0,2]; maintain H in [0.4,0.6]; }',
                 'cell C { state H in [0,1]; maintain Q in [0.4,0.6]; }',
                 'cell C { state H in [0,1]; maintain H in [0.6,0.4]; }',
                 'cell C { cohere; require target_occupancy >= 0.8; }',
                 'cell C { cohere; require overcrowding_fraction <= 2; }',
                 'cell C { cohere; require radius_of_gyration <= 1e999; }',
                 'cell C { cohere }', 'cell C { cohere; };',
                 'cell C { when X is ACTIVE { increase motility; } }',
                 'cell C { input X; when X is ACTIVE { increase motility; } }',
                 'cell C { input X; when X is HIGH { activate X; } }',
                 'cell C { input X; when X is HIGH { increase unknown; } }',
                 'cell C { cohere; budget 0.75; }',
                 'cell C { cohere; require radius_of_gyration <= 0.2; require radius_of_gyration <= 0.1; }',
                 example('03').replace('budget 0.75','budget 0.8'),
                 example('03').replace('[0.40, 0.60]','[0.3, 0.7]')]
        for source in cases:
            with self.subTest(source=source):
                with self.assertRaises(CircleError): compile_source(source)

    def test_token_location(self):
        with self.assertRaisesRegex(CircleError,'2:3: unexpected character'):
            compile_source('cell C {\n  @\n}')

    def test_artifact_tampering(self):
        a=compile_source(example('01'))
        for key,value in [('kernel','arbitrary'),('source_sha256','wrong'),('certification','certified'),('program',{})]:
            b=copy.deepcopy(a);b[key]=value
            with self.subTest(key=key),self.assertRaises(CircleError):load_artifact(b)
        a['unexpected']=True
        with self.assertRaises(CircleError):load_artifact(a)

    def test_portable_roundtrip(self):
        a=compile_source(example('02'));self.assertEqual(a,json.loads(canonical(a)));self.assertEqual(a,compile_source(a['source']))

class RuntimeTests(unittest.TestCase):
    def test_hello_and_signal_change(self):
        a=compile_source(example('00'))
        high=run(a,config={'signals':{'A':'HIGH'}});low=run(a)
        self.assertEqual(high['runs'][0]['motility'],2)
        self.assertEqual(low['runs'][0]['motility'],1)
        self.assertTrue(high['summary']['all_contracts_pass']);self.assertFalse(low['summary']['all_contracts_pass'])
        self.assertEqual(high['runs'][0]['final_states'],{'X':'ACTIVE'})

    def test_synchronous_and_once(self):
        a=compile_source('cell C { state X; state Y; when X is INACTIVE { activate Y; } when Y is ACTIVE { activate X; } when X is ACTIVE { increase motility; } }')
        r=run(a);self.assertEqual(r['trace']['frames'][1]['states'],{'X':'INACTIVE','Y':'ACTIVE'});self.assertEqual(r['runs'][0]['motility'],2)

    def test_conflict_and_oscillation(self):
        for source in ['cell C { state X; when X is INACTIVE { activate X; deactivate X; } }',
                       'cell C { state X; when X is INACTIVE { activate X; } when X is ACTIVE { deactivate X; } }']:
            with self.assertRaises(CircleError):run(compile_source(source))

    def test_contracts_do_not_change_controller(self):
        a=compile_source(example('01'));b=compile_source(example('01').replace('>= 0.80','>= 1.0'))
        x=run(a);y=run(b);self.assertEqual(x['trace'],y['trace'])
        self.assertNotEqual(x['artifact_sha256'],y['artifact_sha256'])

    def test_interval_changes_execution(self):
        x=run(compile_source(example('02')));y=run(compile_source(example('02').replace('[0.40, 0.60]','[0.2, 0.3]')))
        self.assertNotEqual(x['trace'],y['trace'])
        self.assertNotEqual(x['runs'][0]['trigger_interval'],y['runs'][0]['trigger_interval'])

    def test_replay_and_trace_observation(self):
        for prefix in ['01','02','03']:
            a=compile_source(example(prefix));x=run(a,seeds=[12]);y=run(a,seeds=[12],trace=False);z=run(a,seeds=[12])
            self.assertEqual(x,z);self.assertEqual(x['runs'],y['runs']);self.assertEqual(y['trace']['frames'],[])
            self.assertEqual(x['certification'],'not_certified')

    def test_invalid_config(self):
        a=compile_source(example('01'))
        for config in [{'unknown':1},{'noise':float('nan')},{'noise':True},{'noise':-1},{'fields':{'wrong':[0,0,1]}},{'world':'missing'}, {'world':'x','fields':{}}, {'fields':{'attractant':[0,0,0],'hazard':[0,0,1]}}]:
            with self.subTest(config=config),self.assertRaises(CircleError):run(a,config=config)
        for config in [{'context':{'wrong':1}},{'context':{'state_sensor_gain':0}},{'context':{'state_sensor_offset':float('inf')}},{'scenario':'unknown'}]:
            with self.assertRaises(CircleError):run(compile_source(example('02')),config=config)
        for config in [{'geometry':'unknown'},{'interaction':'false'}]:
            with self.assertRaises(CircleError):run(compile_source(example('04')),config=config)

    def test_field_bindings(self):
        a=compile_source(example('01'))
        cfg={'fields':{'attractant':[.92,.5,.64],'hazard':[.58,.45,.13]},'noise':.02}
        x=run(a,config=cfg);self.assertEqual(x['configuration']['world']['id'],'custom')
        cfg['fields']['attractant']=[.05,.5,.64]
        y=run(a,config=cfg);self.assertNotEqual(x['trace'],y['trace'])

    def test_batch_matches_individual_composition(self):
        a=compile_source(example('03'));batch=run(a,seeds=[1,2],trace=False)['runs']
        individual=[run(a,seeds=[seed],trace=False)['runs'][0] for seed in [1,2]]
        self.assertEqual(batch,individual)

    def test_bad_seeds(self):
        for seeds in [[],[0,0],[-1],[True],[1.2],[2**32]]:
            with self.assertRaises(CircleError):run(compile_source(example('00')),seeds=seeds)

    def test_absent_contract_is_not_pass(self):
        r=run(compile_source('cell C { input A; when A is HIGH { increase motility; } }'))
        self.assertIsNone(r['summary']['all_contracts_pass'])

class ArchiveRegressionTests(unittest.TestCase):
    def test_navigation_all_twelve_worlds(self):
        a=compile_source(example('01'))
        for expected in fixture('navigation.json'):
            with self.subTest(world=expected['world']):
                actual=run(a,config={'world':expected['world']},seeds=[expected['seed']],trace=False)['runs'][0]
                for key in ['target_occupancy','forbidden_entry_fraction','mean_final_distance']:
                    self.assertAlmostEqual(actual[key],expected[key],places=11)
                self.assertEqual(actual['research_task_pass'],expected['task_pass'])

    def test_composition_all_48_pairs(self):
        a=compile_source(example('03'))
        for expected in fixture('composition.json'):
            with self.subTest(world=expected['world'],disturbance=expected['disturbance']):
                actual=run(a,config={'world':expected['world'],'disturbance':expected['disturbance']},seeds=[expected['seed']],trace=False)['runs'][0]
                for key in ['target_occupancy','forbidden_entry_fraction','band_occupancy','unsafe_state_fraction','recovery_fraction','mean_final_distance','budget_violations','relaxed_cell_steps','contention_cell_steps','final_risk_debt_cells']:
                    self.assertAlmostEqual(actual[key],expected[key],places=10)
                self.assertEqual(actual['research_task_pass'],bool(expected['joint_pass']))

    def test_homeostasis_two_contexts_six_scenarios_50_seeds(self):
        a=compile_source(example('02'))
        for context in fixture('homeostasis.json'):
            for expected in context['expected']:
                with self.subTest(context=context['context'],scenario=expected['scenario']):
                    rows=run(a,config={'scenario':expected['scenario'],'context':context['context']},seeds=context['seeds'],trace=False)['runs']
                    for key,field in [('band_occupancy','band_occupancy'),('unsafe_state_fraction','unsafe_state_fraction'),('recovery_rate','recovery_fraction'),('mean_abs_error','mean_abs_error'),('task_pass_rate','research_task_pass')]:
                        self.assertAlmostEqual(float(np.mean([r[field] for r in rows])),expected[key],places=11)

    def test_cohesion_frozen_geometry_with_and_without_interaction(self):
        from circle_lang._research.cohesion import core,random_units,metrics
        positions=np.loadtxt(FIX/'cohesion_positions.csv',delimiter=',')
        for expected in fixture('cohesion.json'):
            interaction=expected['mode']=='FROZEN_M96_CHAMPION'
            out=core(positions.copy(),random_units(np.random.default_rng(expected['seed'])),interaction,expected['noise'])
            g,r,o=metrics(out)
            for actual,key in [(g,'giant_component_fraction'),(r,'radius_of_gyration'),(o,'overcrowding_fraction')]:
                self.assertAlmostEqual(actual,expected[key],places=9)

    def test_vendored_integrity(self):
        import circle_lang
        base=Path(circle_lang.__file__).parent
        for entry in data('provenance.json')['files']:
            self.assertEqual(hashlib.sha256((base/entry['destination']).read_bytes()).hexdigest(),entry['sha256'])

class CLITests(unittest.TestCase):
    def call(self,*args):
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):return main(list(args))

    def test_compile_then_verify_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            a=str(Path(d)/'compiled.json');out=str(Path(d)/'run.json');html=str(Path(d)/'run.html')
            source=str(ROOT/'examples/00_hello_cell.circle')
            self.assertEqual(self.call('compile',source,'-o',a),0)
            self.assertEqual(self.call('verify',a,'-o',out),1)
            self.assertEqual(self.call('verify',a,'--config',str(ROOT/'examples/00_signals.json'),'-o',out,'--html',html),0)
            self.assertIn('Recorded execution',Path(html).read_text())
            self.assertEqual(self.call('run',a,'--config',str(ROOT/'examples/00_signals.json'),'--seeds','0,0','-o',out),2)

    def test_output_cannot_replace_input(self):
        source=str(ROOT/'examples/00_hello_cell.circle')
        self.assertEqual(self.call('compile',source,'-o',source),2)

    def test_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text('{"signals":{}, "signals":{"A":"HIGH"}}')
            with self.assertRaises(CircleError):read_json(p)

    def test_report_payload_is_inert(self):
        r=run(compile_source(example('00')));r['evidence']='</script><script>alert(1)</script>'
        html=render_report(r)
        self.assertNotIn(r['evidence'],html);self.assertIn('\\u003c/script',html)

    def test_seed_range(self):
        self.assertEqual(seed_list('3:6'),[3,4,5]);self.assertEqual(seed_list('1,4'),[1,4])
        import argparse
        with self.assertRaises(argparse.ArgumentTypeError): seed_list('0:100000000000')

if __name__=='__main__':unittest.main()
