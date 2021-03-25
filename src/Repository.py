import libarchive

from src.RepositoryItem import RepositoryItem


class Repository:
    """ Simple parser for the arch repository format """
    def __init__(self, name):
        self.name = name
        self.entries = {}
        with libarchive.Archive(self.name, 'r') as a:
            for entry in a:
                if entry.size != 0:
                    package = self.parse_entry(str(a.read(entry.size), 'utf-8'))
                    self.entries[package.name] = package

    def search(self, package):
        self.entries.get(package)

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
        return RepositoryItem(d['filename'], d['name'], d['base'], d['version'], d['desc'], d['csize'], d['isize'],
                              d['md5sum'], d['sha256sum'], d['url'], d['license'], d['arch'], d['builddate'],
                              d['packager'], d.get('depends', []), d.get('optdepends', []), d.get('makedepends', []))

