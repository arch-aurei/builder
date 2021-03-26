import subprocess
import re

from arch.repository_item import RepositoryItem


# This is quite unsafe, but we're trusting the PKGBUILD anyway (we're about to run it)
def parse(file: str):
    ret = subprocess.check_output(['/usr/bin/bash', '-c', f'source {file}; set -o posix; set'],
                                  env={})
    d = {}
    for line in str(ret, 'utf-8').split('\n'):
        kv = line.split('=', 1)
        if len(kv) == 2:
            k = kv[0]
            v = kv[1]
            if k.lower() == k and not k.startswith('_'):
                d[k] = _parse_value(v)
    return RepositoryItem(None, d['pkgname'], None, d['pkgver'], d['pkgdesc'], None, None,
                          None, None, d['url'], d['license'], d['arch'], None, None,
                          d.get('depends', []), d.get('optdepends', []), d.get('makedepends', []))


def _parse_value(v):
    if v.startswith('(') and v.endswith(')'):
        rgx = r"(?:\[[0-9]+\]=\"([^\"]+)\"\s*)"
        res = []
        for match in re.finditer(rgx, v):
            res.append(match.group(1))
        return res

    return v
