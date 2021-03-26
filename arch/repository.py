from collections.abc import Iterable
from datetime import datetime

import libarchive

from arch.repository_item import RepositoryItem


def _flatten(l):
    for el in l:
        if isinstance(el, Iterable) and not isinstance(el, (str, bytes)):
            yield from _flatten(el)
        else:
            yield el


class Repository:
    """ Simple parser for the arch repository format """

    def __init__(self, name):
        self.name = name
        self.entries = {}
        with libarchive.Archive(self.name, 'r') as archive:
            for entry in archive:
                if entry.size != 0:
                    package = self.parse_entry(str(archive.read(entry.size), 'utf-8'))
                    self.entries[package.name] = package

    def search(self, package):
        return self.entries.get(package)

    @staticmethod
    def parse_entry(param):
        d = {}
        current = ""
        for line in param.split("\n"):
            if line.startswith('%') and line.endswith('%'):
                name = line.removeprefix('%').removesuffix('%').lower()
                current = name
            elif line.strip() == "":
                continue
            else:
                if isinstance(d.get(current), str):
                    # Promote to a list
                    a = d[current]
                    d[current] = []
                    d[current].append(a)
                    d[current].append(line)
                elif isinstance(d.get(current), list):
                    d[current].append(line)
                else:
                    d[current] = line
        builddate = datetime.utcfromtimestamp(int(d['builddate'])).strftime('%Y-%m-%dT%H:%M:%SZ')
        return RepositoryItem(d['filename'], d['name'], d['base'], d['version'], d['desc'],
                              d['csize'], d['isize'], d['md5sum'], d['sha256sum'], d['url'],
                              _flatten([d['license']]), d['arch'], builddate, d['packager'],
                              d.get('depends', []), d.get('optdepends', []),
                              d.get('makedepends', []))
