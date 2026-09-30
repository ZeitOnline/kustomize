#!/usr/bin/env python3
"""Convert alembic revisions into goose migrations.

Works when each revision is the usual wrapper that executes a sibling `.sql`
file.  Walks the `down_revision` chain so the migrations come out in the order
they were applied, and names each one after the timestamp of the revision that
introduced it -- that ordering is all goose has.

    ./alembic-to-goose.py backend/migrations/versions backend/migrations

Prints what it writes; read the result before committing.  Revisions that do
more than `op.execute(sql)` are reported and skipped, they need doing by hand.
"""

import re
import sys
from datetime import datetime
from glob import glob
from os import path

WRAPPER = re.compile(r"op\.execute\(\s*sql\s*\)")


def revisions(source):
    """ Read `revision`, `down_revision` and the create date of each file. """
    found = {}
    for name in glob(path.join(source, '*.py')):
        with open(name) as fd:
            code = fd.read()
        if not WRAPPER.search(code):
            print('skipping %s: not a plain `op.execute(sql)` wrapper'
                  % path.basename(name), file=sys.stderr)
            continue

        def value(key):
            match = re.search(r"^%s = '?([^'\n]*)'?" % key, code, re.M)
            found = (match[1] if match else '').strip()
            # the first revision spells its parent `None`, unquoted
            return None if found in ('', 'None') else found

        created = re.search(r'^Create Date: (\S+ \S+)', code, re.M)
        sql = path.splitext(name)[0] + '.sql'
        found[value('revision')] = dict(
            down=value('down_revision'), sql=sql,
            stamp=datetime.fromisoformat(created[1]).strftime('%Y%m%d%H%M%S'),
            name=re.sub(r'^[0-9a-f]+_', '', path.basename(path.splitext(name)[0])))
    return found


def chain(found):
    """ Put the revisions in order, starting at the one without a parent. """
    children = {rev['down']: key for key, rev in found.items()}
    ordered, key = [], children.get(None)
    while key is not None:
        ordered.append(found[key])
        key = children.get(key)
    assert len(ordered) == len(found), \
        'the revisions do not form a single chain, convert them by hand'
    return ordered


def statements(sql):
    """ Split SQL into top-level statements, respecting `$$` and parentheses. """
    parts, buf, dollar, depth = [], '', False, 0
    i = 0
    while i < len(sql):
        if sql.startswith('$$', i):
            dollar = not dollar
            buf += '$$'
            i += 2
            continue
        char = sql[i]
        buf += char
        i += 1
        if not dollar and char in '()':
            depth += 1 if char == '(' else -1
        if char == ';' and not dollar and depth == 0:
            parts.append(buf.strip())
            buf = ''
    if buf.strip():
        parts.append(buf.strip())
    return parts


def convert(sql):
    # goose runs each migration in a transaction of its own
    sql = re.sub(r'^\s*BEGIN;\s*', '', sql)
    sql = re.sub(r'\s*COMMIT;\s*$', '', sql)
    blocks = []
    for stmt in statements(sql):
        # goose splits on semicolons, so anything with one before its end --
        # a function body, a rule -- has to be fenced off
        if ';' in stmt[:-1]:
            blocks.append('-- +goose StatementBegin\n%s\n-- +goose StatementEnd' % stmt)
        else:
            blocks.append(stmt)
    out = blocks[:1]
    for block in blocks[1:]:
        # keep neighbouring one-liners together, give the rest room to breathe
        single = '\n' not in block.strip() and '\n' not in out[-1].strip()
        out.append(('\n' if single else '\n\n\n') + block)
    return '-- +goose Up\n\n' + ''.join(out).rstrip() + '\n'


def main(source, target):
    for revision in chain(revisions(source)):
        with open(revision['sql']) as fd:
            sql = fd.read()
        name = '%(stamp)s_%(name)s.sql' % revision
        with open(path.join(target, name), 'w') as fd:
            fd.write(convert(sql))
        print('wrote', name)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit('usage: %s <versions-dir> <target-dir>'
                 % path.basename(sys.argv[0]))
    main(*sys.argv[1:])
