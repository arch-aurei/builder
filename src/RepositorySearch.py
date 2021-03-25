import pyalpm
from pyalpm import Handle
import requests

from src.RepositoryItem import RepositoryItem

_alpm_handle = Handle('/', '/var/lib/pacman')
_repos = [_alpm_handle.register_syncdb('core', pyalpm.SIG_DATABASE_OPTIONAL),
          _alpm_handle.register_syncdb('community', pyalpm.SIG_DATABASE_OPTIONAL),
          _alpm_handle.register_syncdb('extra', pyalpm.SIG_DATABASE_OPTIONAL),
          _alpm_handle.register_syncdb('multilib', pyalpm.SIG_DATABASE_OPTIONAL)]


def local_search(package: str):
    """ Search for a package in the systems default repos """
    for repo in _repos:
        # p = repo.search(f"^{package}$")
        p = repo.get_pkg(package)
        if p is not None:
            return RepositoryItem(p.filename, p.name, p.base, p.version, p.desc, p.size, p.isize, p.md5sum,
                                  p.sha256sum, p.url, p.licenses, p.arch, p.builddate, p.packager, p.depends,
                                  p.optdepends, p.makedepends)
    return None


def aur_search(package: str):
    """ Search for a package on the AUR """
    params = {'v': 5, 'type': 'info', 'arg': [package]}
    r = requests.get('https://aur.archlinux.org/rpc/', params=params)
    res = r.json()
    if res['resultcount'] != 1:
        return None
    else:
        r = res['results'][0]
        return RepositoryItem(None, r['Name'], r['PackageBase'], r['Version'], r['Description'], None, None,
                              None, None, r['URL'], r['License'], None, None, None, r.get('Depends', []),
                              r.get('OptDepends', []), r.get('MakeDepends', []))
