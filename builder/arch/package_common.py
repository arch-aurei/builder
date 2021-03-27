import re


def verdeps_dict(xs: list[str]) -> list[dict[str, str]]:
    pretty_xs = []
    for item in xs:
        res = re.search(r"^(?P<name>[^<>=]+)\s*(?P<cons>[<>=]+.*)*", item)
        if res is not None and res.groupdict().get('cons') is not None:
            pretty_xs.append(res.groupdict())
        else:
            pretty_xs.append({'name': item})
    return pretty_xs


def optdeps_dict(xs: list[str]) -> list[dict[str, str]]:
    pretty_xs = []
    for item in xs:
        kv = item.split(':', maxsplit=1)
        if len(kv) == 2:
            pretty_xs.append({'name': kv[0].strip(), 'description': kv[1].strip()})
        else:
            pretty_xs.append({'name': item})
    return pretty_xs
