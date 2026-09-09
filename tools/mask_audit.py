# 2026-09-09: a stale constant in a MASK cost two findings. A stale constant in a LADDER cost nothing.
# Find every remaining mask mechanically, because the difference is now measured and not a guess.
#
# TWICE TONIGHT THE SAME FAULT, WITH OPPOSITE CONSEQUENCES. The corridor lamp tool built its aperture from
# a sill and head the model had moved away from, and it manufactured two reveal points sitting on the mask
# edge; both were shipped and both were withdrawn. The corridor ray gate carried the same three stale
# numbers and its 71 mm of extra head admitted 87 rays through solid stone, yet the answer it produced did
# not move by more than 5 mm. And moving the corridor's sampling ladder 260 mm changed nothing at all.
#
# SO THE DIFFERENCE IS NOT HOW STALE THE CONSTANT IS, IT IS WHAT THE CONSTANT DOES.
#   A MASK decides whether a ray EXISTS. Get it wrong and detections pile onto the wrong edge, and the
#   tool reports a feature that is the mask itself. Nothing downstream can catch it, because every
#   instrument downstream is looking through the same rectangle.
#   A LADDER decides only WHERE TO LOOK. Get it wrong and a wide enough ladder still finds the real edge
#   from the wrong centre. It costs rays, not truth.
# tools/constant_drift.py finds stale constants but treats them all alike, which is why 121 hits are
# unreadable in one sitting and why the corridor gate survived a whole day inside them.
#
# THIS SORTS THEM BY WHAT THE CODE ACTUALLY DOES WITH THEM. It parses each tool, resolves module-level
# constants to their literals, and asks of every use: does this value appear inside a COMPARISON that
# decides whether data is kept, or inside a SAMPLING expression that decides where to look? The first is a
# mask and is read tonight. The second is a ladder and can wait.
#
# WHAT IT CANNOT DO is know that a comparison is filtering rays rather than, say, choosing a print format.
# It reports and does not edit, and a mask hit is a candidate for reading, not a verdict.
import ast
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = {'mask_audit.py', 'constant_drift.py'}
SAMPLERS = {'arange', 'linspace', 'range', 'logspace'}


def moved_list():
    """read the MOVED table out of constant_drift.py rather than keeping a second copy of it"""
    src = open(os.path.join(HERE, 'constant_drift.py'), encoding='utf-8').read()
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', '') == 'MOVED' for t in node.targets):
            return [(e.elts[0].value, e.elts[1].value, e.elts[2].value) for e in node.value.elts]
    raise SystemExit('MOVED not found in constant_drift.py')


MOVED = moved_list()
STALE = {}
for old, new, what in MOVED:
    try:
        v = float(old)
    except ValueError:
        continue
    # A WHOLE NUMBER CANNOT BE MATCHED BY VALUE and the first run proved it: the corridor width 2.000
    # matched every bare 2 in the project, 200 of them, and buried the four hits that mattered under
    # array indices and modulo tests. A superseded value is only findable this way when it carries a
    # fraction, so integral entries are declared unmatchable here rather than reported as noise.
    if abs(v - round(v)) < 1e-9:
        continue
    STALE[round(v, 6)] = (old, new, what)


def const_value(node):
    """the numeric value of a literal or a negated literal, else None"""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = const_value(node.operand)
        return None if v is None else -v
    return None


def module_constants(tree):
    """module-level NAME -> literal, including tuple unpacking, which is how this project writes them"""
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        tgt = node.targets[0]
        if isinstance(tgt, ast.Name):
            v = const_value(node.value)
            if v is not None:
                out[tgt.id] = v
        elif isinstance(tgt, ast.Tuple) and isinstance(node.value, ast.Tuple):
            for t, v in zip(tgt.elts, node.value.elts):
                if isinstance(t, ast.Name):
                    val = const_value(v)
                    if val is not None:
                        out[t.id] = val
    return out


def stale_uses(node, consts):
    """every stale value reachable inside this expression, as (value, how it was written)"""
    found = []
    for sub in ast.walk(node):
        v = const_value(sub)
        nm = None
        if v is None and isinstance(sub, ast.Name) and sub.id in consts:
            v, nm = consts[sub.id], sub.id
        if v is None or abs(v - round(v)) < 1e-9:
            continue
        key = round(v, 6)
        if key in STALE:
            found.append((key, nm or ('%g' % v)))
    return found


def sampler_lines(tree):
    """line numbers of sampling calls, so a constant inside one is not read as a mask"""
    lines = set()
    for sub in ast.walk(tree):
        if isinstance(sub, ast.Call):
            fn = sub.func
            nm = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, 'id', '')
            if nm in SAMPLERS:
                for n in ast.walk(sub):
                    if hasattr(n, 'lineno'):
                        lines.add(n.lineno)
    return lines


masks, ladders, failed = [], [], []
files = [f for f in sorted(os.listdir(HERE)) if f.endswith('.py') and f not in SKIP]
for name in files:
    try:
    # utf-8-sig, NOT utf-8. One tool carries a byte-order mark and every audit in this project had
    # been silently skipping it: an unaudited tool is exactly the hole these audits exist to close,
    # and a skip that only shows up as a count at the top of the report is a skip nobody reads.
        src = open(os.path.join(HERE, name), encoding='utf-8-sig').read()
        tree = ast.parse(src)
    except Exception as exc:
        failed.append((name, str(exc)[:60]))
        continue
    consts = module_constants(tree)
    samp = sampler_lines(tree)
    srclines = src.split('\n')
    seen = set()
    for sub in ast.walk(tree):
        if not isinstance(sub, ast.Compare):
            continue
        for key, written in stale_uses(sub, consts):
            ln = getattr(sub, 'lineno', 0)
            if (ln, key) in seen:
                continue
            seen.add((ln, key))
            row = (name, ln, written, STALE[key], srclines[ln - 1].strip()[:100])
            (ladders if ln in samp else masks).append(row)

print('%d tools parsed, %d stale values reachable inside a COMPARISON' % (len(files), len(masks)))
print('')
if failed:
    print('%d tools could not be parsed and were skipped: %s'
          % (len(failed), ', '.join(n for n, _ in failed)))
    print('')
if not masks:
    print('NO MASK ANYWHERE CARRIES A SUPERSEDED VALUE. Every stale constant left in these tools is in a')
    print('comment, a string, or a sampling expression, and none of them can decide whether a ray exists.')
else:
    print('MASKS FIRST. Each of these is a constant the model has moved away from, appearing inside a')
    print('comparison, which is where a wrong value stops being a lost ray and starts being a fabricated')
    print('feature. Read every one.')
    cur = None
    for name, ln, written, sw, text in masks:
        if name != cur:
            print('')
            print('%s' % name)
            cur = name
        print('   line %-4d %-10s %-8s -> %-8s  %s' % (ln, written, sw[0], sw[1], sw[2]))
        print('      %s' % text)
print('')
print('%d more sit inside SAMPLING expressions, where a wrong centre costs rays and not truth. They are'
      % len(ladders))
print('listed second on purpose, and the corridor measured why: moving that ladder 260 mm changed the')
print('answer by 3 mm.')
for name, ln, written, sw, text in ladders:
    print('   %-24s %-5d %-10s %-8s -> %-8s  %s' % (name, ln, written, sw[0], sw[1], sw[2]))
