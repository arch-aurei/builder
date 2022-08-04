import os
import subprocess
from typing import Union, cast
from typing import Optional

from loguru import logger
from pydantic import BaseModel

from builder.arch.package_common import verdeps_dict, optdeps_dict
from builder.util.misc import listify


class PkgBuildPackage(BaseModel):
    pkgbase: str
    pkgname: str
    pkgdesc: str
    pkgver: str
    pkgrel: str
    url: Optional[str]
    arch: list[str]
    license: list[str]
    makedepends: list[dict[str, str]]
    depends: list[dict[str, str]]
    provides: list[str]
    options: list[str]
    optdepends: list[dict[str, str]]
    source: list[str]
    sha256sums: list[str]
    sha512sums: list[str]


def parse(package_dir: str) -> list[PkgBuildPackage]:
    logger.debug(f"Reading PKGBUILD file for {package_dir}")
    logger.debug(f"Contents of directory {os.listdir(package_dir)}")
    ret = subprocess.check_output(
        ['makepkg', '--printsrcinfo'], cwd=package_dir)
    pkgbase: dict[str, dict[str, Union[str, list[str]]]] = {}
    pkgname: dict[str, dict[str, Union[str, list[str]]]] = {}

    cur_base = None
    cur_name = None
    for line in str(ret, 'utf-8').split('\n'):
        if line.strip() == '':
            continue

        kv = line.split('=', 1)
        k = kv[0].strip()
        v = kv[1].strip()
        if k == 'pkgbase':
            cur_base = v
            cur_name = None
        elif k == 'pkgname':
            cur_base = None
            cur_name = v

        target = {}
        if cur_base is not None:
            if pkgbase.get(cur_base) is None:
                pkgbase[cur_base] = {}
            target = pkgbase[cur_base]
        elif cur_name is not None:
            if pkgname.get(cur_name) is None:
                pkgname[cur_name] = {}
            target = pkgname[cur_name]

        if target.get(k) is None:
            target[k] = v
        else:
            old_v = target[k]
            if isinstance(old_v, list):
                old_v.append(v)
            elif isinstance(old_v, str):
                target[k] = [old_v, v]

    packages = []
    for name, package in pkgname.items():
        # for now, assume theres one base
        p = package | next(iter(pkgbase.values()))

        depends = verdeps_dict(listify(p, 'depends'))
        makedepends = verdeps_dict(listify(p, 'makedepends'))
        optdepends = optdeps_dict(listify(p, 'optdepends'))
        packages.append(
            PkgBuildPackage(pkgbase=p['pkgbase'], pkgname=p['pkgname'], pkgdesc=p['pkgdesc'], pkgver=p['pkgver'],
                            pkgrel=p['pkgrel'], url=p.get('url'), arch=['arch'], license=listify(p, 'license'),
                            makedepends=makedepends, depends=depends, provides=listify(
                                p, 'provides'),
                            options=listify(p, 'options'), optdepends=optdepends, source=listify(p, 'source'),
                            sha256sums=listify(p, 'sha256sums'), sha512sums=listify(p, 'sha512sums')))

    return packages
