from typing import Optional, Union

import libarchive
from pydantic import BaseModel

from builder.arch.package_common import verdeps_dict, optdeps_dict
from builder.util.misc import listify


class RepoPackage(BaseModel):
    """ Represents a package in a repository, this is the minimum across local, aur and repo """
    filename: str
    name: str
    base: str
    version: str
    desc: str
    csize: int
    isize: int
    md5sum: Optional[str]
    sha256sum: Optional[str]
    b2sum: Optional[str]
    pgpsig: str
    url: Optional[str]
    license: list[str]
    arch: str
    builddate: int
    packager: str
    conflicts: list[str]
    provides: list[str]
    depends: list[dict[str, str]]
    optdepends: list[dict[str, str]]
    makedepends: list[dict[str, str]]


class Repository:
    """ Simple parser for the arch repository format """

    def __init__(self, name: str):
        self.name = name
        self.entries = {}
        with libarchive.Archive(self.name, 'r') as archive:
            for entry in archive:
                if entry.size != 0:
                    package = self.parse_entry(
                        str(archive.read(entry.size), 'utf-8'))
                    self.entries[package.name] = package

    def search(self, package: str) -> Optional[RepoPackage]:
        return self.entries.get(package)

    @staticmethod
    def parse_entry(param: str) -> RepoPackage:
        d: dict[str, Union[list[str], str]] = {}
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

        pretty_depends = verdeps_dict(listify(d, 'depends'))
        pretty_make_depends = verdeps_dict(listify(d, 'makedepends'))
        pretty_opt_depends = optdeps_dict(listify(d, 'optdepends'))

        return RepoPackage(filename=d['filename'], name=d['name'], base=d['base'], version=d['version'], desc=d['desc'],
                           csize=int(d['csize']), isize=int(d['isize']), md5sum=d.get('md5sum', ''), sha256sum=d.get('sha256sum', ''),
                           b2sum=d.get('b2sum', ''), pgpsig=d['pgpsig'], url=d.get('url'), license=listify(d, 'license'), arch=d['arch'],
                           builddate=int(d['builddate']), packager=d['packager'],
                           conflicts=listify(d, 'conflicts'), provides=listify(d, 'provides'),
                           depends=pretty_depends, optdepends=pretty_opt_depends,
                           makedepends=pretty_make_depends)
