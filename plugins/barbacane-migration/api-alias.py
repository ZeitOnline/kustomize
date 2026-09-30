""" Derives a prefixed variant of an OpenAPI contract.

Where nginx strips a prefix (typically `/api`) before proxying, the gateway
still has to know those routes, because Barbacane only forwards paths the
contract declares. A spec may not repeat an operationId, so the routes cannot
simply be aliased -- generate them at build time instead:

    python api-alias.py specs/api.yaml > specs/api-alias.yaml

Needs pyyaml. Adjust `prefix`/`suffix` below if the project strips something
other than `/api`.
"""

from sys import argv, stdout

from yaml import safe_dump, safe_load


def alias(spec, prefix='/api', suffix='ViaApi'):
    paths = {}
    for path, item in spec['paths'].items():
        item = dict(item)
        for method, operation in item.items():
            if isinstance(operation, dict) and 'operationId' in operation:
                item[method] = dict(
                    operation, operationId=operation['operationId'] + suffix)
        paths[prefix + path] = item
    derived = dict(
        openapi=spec['openapi'],
        info=dict(spec['info'], title=spec['info']['title'] + f' ({prefix})'),
        paths=paths,
        components=spec.get('components', {}))
    # the root requirement is what admits the credential headers, so the
    # derived document is unusable without it
    if 'security' in spec:
        derived['security'] = spec['security']
    return derived


if __name__ == '__main__':
    with open(argv[1]) as fd:
        safe_dump(alias(safe_load(fd)), stdout, sort_keys=False)
