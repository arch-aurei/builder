from typing import Optional

import pyalpm
import requests
from loguru import logger
from pyalpm import Handle
from pydantic import BaseModel

from builder.arch.package_common import verdeps_dict, optdeps_dict
from builder.util.misc import listify

_alpm_handle = Handle('/', '/var/lib/pacman')
_repos = [_alpm_handle.register_syncdb('core', pyalpm.SIG_DATABASE_OPTIONAL),
          _alpm_handle.register_syncdb(
              'community', pyalpm.SIG_DATABASE_OPTIONAL),
          _alpm_handle.register_syncdb('extra', pyalpm.SIG_DATABASE_OPTIONAL),
          _alpm_handle.register_syncdb('multilib', pyalpm.SIG_DATABASE_OPTIONAL)]


class LocalPackage(BaseModel):
    """ Represents a local package from a repo (a "syncdb") """

    arch: str
    """ target architecture """

    backup: list[tuple[str, str]]
    """ list of tuples (filename, md5sum) """

    base: str
    """package base name"""

    base64_sig: str
    """GPG signature encoded as base64"""

    builddate: int
    """building time"""

    checkdepends: list[str]
    """list of check dependencies"""

    conflicts: list[str]
    """list of conflicts"""

    db: Optional[str]
    """the database from which the package comes from, or None"""

    depends: list[dict[str, str]]
    """list of dependencies"""

    desc: str
    """package desc"""

    download_size: int
    """predicted download size for this package"""

    filename: str
    """package filename"""

    files: list[str]
    """list of installed files"""

    groups: list[str]
    """list of package groups"""

    has_scriptlet: bool
    """True if the package has an install script"""

    installdate: int
    """install time"""

    isize: int
    """installed size"""

    licenses: list[str]
    """list of licenses"""

    makedepends: list[dict[str, str]]
    """list of make dependencies"""

    md5sum: str = ''
    """package md5sum"""

    name: str
    """package name"""

    optdepends: list[dict[str, str]]
    """list of optional dependencies"""

    packager: str
    """packager name"""

    provides: list[str]
    """list of provided package names"""

    reason: int
    """install reason (0 = explicit, 1 = depend)"""

    replaces: list[str]
    """list of replaced packages"""

    sha256sum: str
    """package sha256sum as hexadecimal digits"""

    size: int
    """package size"""

    url: Optional[str]
    """package URL"""

    version: str
    """package version"""


class AURPackage(BaseModel):
    """ Represents a package on the AUR """

    id: int
    name: str
    package_base_id: int
    package_base: str
    version: str
    description: str
    URL: str
    num_votes: int
    popularity: float
    out_of_date: Optional[int]
    maintainer: str
    first_submitted: int
    last_modified: int
    URL_path: str
    depends: list[dict[str, str]]
    makedepends: list[dict[str, str]]
    optdepends: list[dict[str, str]]
    checkdepends: list[str]
    conflicts: list[str]
    provides: list[str]
    replaces: list[str]
    groups: list[str]
    license: list[str]
    keywords: list[str]


def local_search(package: str) -> Optional[LocalPackage]:
    """ Search for a package in the systems default repos """

    logger.debug(f"Looking up {package} locally")
    for repo in _repos:
        pkg: pyalpm.Package = repo.get_pkg(package)
        if pkg is None:
            # It could be a provides, if so lets take the first
            pkgs = repo.search(f"^{package}$")
            if len(pkgs) > 0:
                pkg = pkgs[0]
        if pkg is not None:
            depends = verdeps_dict(pkg.depends)
            makedepends = verdeps_dict(pkg.makedepends)
            optdepends = optdeps_dict(pkg.optdepends)

            return LocalPackage(arch=pkg.arch, backup=pkg.backup, base=pkg.base, base64_sig=pkg.base64_sig,
                                builddate=pkg.builddate, checkdepends=pkg.checkdepends, conflicts=pkg.conflicts,
                                db=pkg.db.name, depends=depends, desc=pkg.desc, download_size=pkg.download_size,
                                filename=pkg.filename, files=pkg.files, groups=pkg.groups,
                                has_scriptlet=pkg.has_scriptlet, installdate=pkg.installdate,
                                isize=pkg.isize, licenses=pkg.licenses, makedepends=makedepends, md5sum=pkg.md5sum or '',
                                name=pkg.name, optdepends=optdepends, packager=pkg.packager, provides=pkg.provides,
                                reason=pkg.reason, replaces=pkg.replaces, sha256sum=pkg.sha256sum, size=pkg.size,
                                url=pkg.url,
                                version=pkg.version)

    logger.debug(f"Package {package} was not found locally")
    return None


def aur_search(package: str) -> Optional[AURPackage]:
    """ Search for a package on the AUR """

    logger.debug(f"Looking up {package} on the AUR")
    params = {'v': '5', 'type': 'info', 'arg': [package]}
    r = requests.get('https://aur.archlinux.org/rpc/', params=params)
    res = r.json()
    if res['resultcount'] != 1:
        logger.debug(f"Package {package} was not found on the AUR")
        return None

    p = res['results'][0]

    depends = verdeps_dict(listify(p, 'Depends'))
    makedepends = verdeps_dict(listify(p, 'MakeDepends'))
    optdepends = optdeps_dict(listify(p, 'OptDepends'))

    return AURPackage(id=p['ID'], name=p['Name'], package_base_id=p['PackageBaseID'], package_base=p['PackageBase'],
                      version=p['Version'], description=p['Description'], URL=p.get('URL'), num_votes=p['NumVotes'],
                      popularity=p['Popularity'], out_of_date=p['OutOfDate'], maintainer=p['Maintainer'],
                      first_submitted=p['FirstSubmitted'], last_modified=p['LastModified'], URL_path=p['URLPath'],
                      depends=depends, makedepends=makedepends, optdepends=optdepends,
                      checkdepends=listify(p, 'CheckDepends'), conflicts=listify(p, 'Conflicts'),
                      provides=listify(p, 'Provides'), replaces=listify(p, 'Replaces'), groups=listify(p, 'Groups'),
                      license=p['License'], keywords=p['Keywords'])
