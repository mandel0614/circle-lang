"""Circle 0.1: strict, finite-profile declarative language and portable BioIR."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib
import json
import math
import re

VERSION = '0.1.0rc1'
SCHEMA = 'circle.bioir.v1'
KERNELS = {'logic': 'm0.5-fixed-point', 'navigation': 'm8.6-r1-abstract',
           'homeostasis': 'm6.3-context-v1', 'composition': 'm7.18-viability-debt-v3',
           'cohesion': 'm9.12-frozen-abstract'}
METRICS = {
    'logic': {'motility', 'division', 'secretion'},
    'navigation': {'target_occupancy', 'forbidden_entry_fraction', 'mean_final_distance'},
    'homeostasis': {'band_occupancy', 'unsafe_state_fraction', 'recovery_fraction', 'mean_abs_error'},
    'composition': {'target_occupancy', 'forbidden_entry_fraction', 'band_occupancy',
                    'unsafe_state_fraction', 'recovery_fraction', 'budget_violations', 'mean_final_distance'},
    'cohesion': {'giant_component_fraction', 'radius_of_gyration', 'overcrowding_fraction'},
}

class CircleError(ValueError):
    """Invalid source, artifact, configuration, or execution."""

@dataclass(frozen=True)
class Token:
    text: str
    line: int
    column: int

@dataclass(frozen=True)
class Condition:
    name: str
    value: str

@dataclass(frozen=True)
class Action:
    verb: str
    target: str

@dataclass(frozen=True)
class Rule:
    conditions: tuple[Condition, ...]
    actions: tuple[Action, ...]

@dataclass(frozen=True)
class Constraint:
    metric: str
    op: str
    value: float

@dataclass(frozen=True)
class Program:
    name: str
    profile: str
    inputs: tuple[str, ...]
    states: tuple[str, ...]
    continuous: str | None
    interval: tuple[float, float] | None
    toward: str | None
    avoid: str | None
    budget: float | None
    rules: tuple[Rule, ...]
    constraints: tuple[Constraint, ...]

_PATTERN = re.compile(r'(?P<space>\s+)|(?P<comment>\#[^\n]*)|(?P<number>-?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)|(?P<id>[A-Za-z_][A-Za-z_0-9]*)|(?P<symbol>>=|<=|==|[{}\[\],;])')

def tokenize(source: str) -> list[Token]:
    out = []; pos = 0; line = 1; col = 1
    while pos < len(source):
        m = _PATTERN.match(source, pos)
        if not m:
            raise CircleError(f'{line}:{col}: unexpected character {source[pos]!r}')
        word = m.group()
        if m.lastgroup not in {'space', 'comment'}:
            out.append(Token(word, line, col))
        if '\n' in word:
            line += word.count('\n'); col = len(word.rsplit('\n', 1)[1]) + 1
        else:
            col += len(word)
        pos = m.end()
    return out + [Token('<EOF>', line, col)]

class Parser:
    def __init__(self, source):
        self.tokens = tokenize(source); self.i = 0

    @property
    def t(self): return self.tokens[self.i]

    def fail(self, message):
        raise CircleError(f'{self.t.line}:{self.t.column}: {message}; found {self.t.text!r}')

    def take(self, expected=None):
        t = self.t
        if expected is not None and t.text != expected: self.fail(f'expected {expected!r}')
        if t.text == '<EOF>': self.fail('unexpected end of source')
        self.i += 1
        return t.text

    def name(self):
        if not re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', self.t.text): self.fail('expected identifier')
        return self.take()

    def number(self):
        try: x = float(self.t.text)
        except ValueError: self.fail('expected finite number')
        if not math.isfinite(x): self.fail('expected finite number')
        self.take(); return x

    def interval(self):
        self.take('['); lo = self.number(); self.take(','); hi = self.number(); self.take(']')
        if not 0 <= lo < hi <= 1: self.fail('interval must satisfy 0 <= low < high <= 1')
        return (lo, hi)

    def parse(self):
        self.take('cell'); name = self.name(); self.take('{')
        inputs = []; states = []; continuous = None; interval = None
        toward = avoid = budget = None; cohere = False; rules = []; constraints = []
        symbols = set(); maintain_state = None
        while self.t.text != '}':
            kind = self.take()
            if kind in {'input', 'state'}:
                key = self.name()
                if key in symbols: self.fail(f'duplicate symbol {key}')
                symbols.add(key)
                if kind == 'input': inputs.append(key)
                elif self.t.text == 'in':
                    if continuous is not None: self.fail('only one continuous state is supported')
                    self.take('in'); domain = self.interval()
                    if domain != (0., 1.): self.fail('continuous state domain must be [0, 1]')
                    continuous = key
                else: states.append(key)
            elif kind == 'maintain':
                if maintain_state is not None: self.fail('duplicate maintain behavior')
                maintain_state = self.name(); self.take('in'); interval = self.interval()
            elif kind == 'migrate':
                if toward is not None: self.fail('duplicate migrate behavior')
                self.take('toward'); toward = self.name()
            elif kind == 'avoid':
                if avoid is not None: self.fail('duplicate avoid behavior')
                avoid = self.name()
            elif kind == 'budget':
                if budget is not None: self.fail('duplicate budget')
                budget = self.number()
            elif kind == 'cohere':
                if cohere: self.fail('duplicate cohere behavior')
                cohere = True
            elif kind == 'require':
                metric = self.name(); op = self.take()
                if op not in {'>=', '<=', '=='}: self.fail('comparison must be >=, <= or ==')
                constraints.append(Constraint(metric, op, self.number()))
            elif kind == 'when':
                conditions = []
                while True:
                    key = self.name(); self.take('is'); value = self.name()
                    conditions.append(Condition(key, value))
                    if self.t.text != 'and': break
                    self.take('and')
                self.take('{'); actions = []
                while self.t.text != '}':
                    verb = self.take()
                    if verb not in {'activate', 'deactivate', 'increase', 'decrease'}: self.fail('unknown rule action')
                    actions.append(Action(verb, self.name())); self.take(';')
                self.take('}')
                if not actions: self.fail('rule must have an action')
                rules.append(Rule(tuple(conditions), tuple(actions)))
                continue
            else: self.fail(f'unsupported statement {kind!r}')
            self.take(';')
        self.take('}')
        if self.t.text != '<EOF>': self.fail('unexpected content after program')
        if (toward is None) != (avoid is None): self.fail('navigation requires migrate and avoid together')
        if (continuous is None) != (maintain_state is None) or (continuous is not None and continuous != maintain_state):
            self.fail('maintain must name the declared continuous state')
        if toward is not None and (toward == avoid or set(inputs) != {toward, avoid}):
            self.fail('navigation requires exactly two distinct declared inputs, used by migrate and avoid')
        if cohere and (inputs or states or continuous or toward or rules or budget is not None): self.fail('cohere cannot be combined with other behaviors in 0.1')
        if rules and (continuous or toward or cohere or budget is not None): self.fail('logical rules cannot be combined with continuous behaviors in 0.1')
        if states and not rules: self.fail('logical states require rules')
        if not rules and inputs and toward is None: self.fail('unused inputs')
        if toward and continuous: profile = 'composition'
        elif toward: profile = 'navigation'
        elif continuous: profile = 'homeostasis'
        elif cohere: profile = 'cohesion'
        elif rules: profile = 'logic'
        else: self.fail('program has no executable behavior')
        if profile == 'composition' and (budget != .75 or interval != (.4, .6)):
            self.fail('composition v3 requires budget 0.75 and maintain interval [0.4, 0.6]')
        if profile != 'composition' and budget is not None: self.fail('budget is supported only for composition')
        for rule in rules:
            for cond in rule.conditions:
                choices = {'HIGH','LOW'} if cond.name in inputs else {'ACTIVE','INACTIVE'} if cond.name in states else set()
                if cond.value not in choices: self.fail(f'invalid condition {cond.name} is {cond.value}')
            for action in rule.actions:
                targets = states if action.verb in {'activate','deactivate'} else METRICS['logic']
                if action.target not in targets: self.fail(f'invalid action target {action.target}')
        seen = set()
        for c in constraints:
            if c.metric not in METRICS[profile]: self.fail(f'unsupported {profile} metric {c.metric}')
            if c.metric in seen: self.fail(f'duplicate contract metric {c.metric}')
            if c.value < 0: self.fail('contract thresholds must be nonnegative')
            if ('fraction' in c.metric or 'occupancy' in c.metric) and c.value > 1: self.fail('fraction thresholds must be <= 1')
            seen.add(c.metric)
        return Program(name, profile, tuple(inputs), tuple(states), continuous, interval, toward, avoid,
                       budget, tuple(rules), tuple(constraints))

def parse(source: str) -> Program:
    if not isinstance(source, str): raise CircleError('source must be text')
    return Parser(source).parse()

def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)

def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def compile_source(source: str) -> dict:
    p = parse(source)
    return {'schema': SCHEMA, 'language_version': VERSION, 'source': source,
            'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
            'program': json.loads(canonical(asdict(p))), 'kernel': KERNELS[p.profile],
            'backend': 'abstract-cpu', 'certification': 'not_certified',
            'contract_scope': 'each_run', 'compilation': 'validated_template_lowering'}

def load_artifact(value: dict) -> Program:
    if not isinstance(value, dict) or not isinstance(value.get('source'), str): raise CircleError('expected a Circle BioIR artifact')
    rebuilt = compile_source(value['source'])
    if canonical(value) != canonical(rebuilt): raise CircleError('artifact differs from validated source or uses an unsupported version; recompile it')
    return parse(value['source'])
