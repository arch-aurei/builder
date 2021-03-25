from src import RepositorySearch
from src.Repository import Repository


# Find a packages dependencies
# Dependencies can either be:
# - in a local syncdb (core etc)
# - on the aur
# - in our local repo
# - part of a pkgbuild itself
def resolve(package):
    for pkg in package.depends:
        print(f"Looking for dependency: {pkg}")
        local = RepositorySearch.local_search(pkg)
        if local is not None:
            print(f"Found package dependency locally")
            continue
        remote = RepositorySearch.aur_search(pkg)
        if remote is not None:
            print(f"Found package on the AUR")
            continue
        repo = Repository("aurei")
        repo_pkg = repo.search(package)
        if repo_pkg is not None:
            print(f"Found package in repo")
            return repo_pkg