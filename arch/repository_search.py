import pyalpm
from pyalpm import Handle
import requests

from arch.repository_item import RepositoryItem

_alpm_handle = Handle('/', '/var/lib/pacman')
_repos = [_alpm_handle.register_syncdb('core', pyalpm.SIG_DATABASE_OPTIONAL),
          _alpm_handle.register_syncdb('community', pyalpm.SIG_DATABASE_OPTIONAL),
          _alpm_handle.register_syncdb('extra', pyalpm.SIG_DATABASE_OPTIONAL),
          _alpm_handle.register_syncdb('multilib', pyalpm.SIG_DATABASE_OPTIONAL)]


def local_search(package: str):
    """ Search for a package in the systems default repos """
    for repo in _repos:
        pkg = repo.get_pkg(package)
        if pkg is None:
            # It could be a provides, if so lets take the first
            pkgs = repo.search(f"^{package}$")
            if len(pkgs) > 0:
                pkg = pkgs[0]
        if pkg is not None:
            return RepositoryItem(pkg.filename, pkg.name, pkg.base, pkg.version, pkg.desc, pkg.size,
                                  pkg.isize, pkg.md5sum, pkg.sha256sum, pkg.url, pkg.licenses, pkg.arch,
                                  pkg.builddate, pkg.packager, pkg.depends, pkg.optdepends,
                                  pkg.makedepends)

    return None


def aur_search(package: str):
    """ Search for a package on the AUR """
    params = {'v': 5, 'type': 'info', 'arg': [package]}
    r = requests.get('https://aur.archlinux.org/rpc/', params=params)
    res = r.json()
    if res['resultcount'] != 1:
        return None

    r = res['results'][0]
    return RepositoryItem(None, r['Name'], r['PackageBase'], r['Version'], r['Description'],
                          None, None, None, None, r['URL'], r['License'], None, None, None,
                          r.get('Depends', []), r.get('OptDepends', []),
                          r.get('MakeDepends', []))
