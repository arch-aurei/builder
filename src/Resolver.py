from loguru import logger

from src import RepositorySearch
from src.Repository import Repository
from src.RepositoryItem import RepositoryItem


class Strategy:
    def __init__(self, package: RepositoryItem):
        self.package = package


class AURInstall(Strategy):
    pass


class LocalInstall(Strategy):
    pass


# Find a packages dependencies
# Dependencies can either be:
# - in a local syncdb (core etc)
# - on the aur
# - in our local repo
# - part of a pkgbuild itself
def resolve(package):
    actions = []
    for pkg in package.depends:
        logger.info(f"Looking for dependency: {pkg}")
        local = RepositorySearch.local_search(pkg)
        if local is not None:
            logger.info(f"Found package dependency locally")
            actions.append(LocalInstall(local))
            continue
        remote = RepositorySearch.aur_search(pkg)
        if remote is not None:
            logger.info(f"Found package on the AUR")
            actions.append(AURInstall(remote))
            continue
        repo = Repository("aurei")
        repo_pkg = repo.search(package)
        if repo_pkg is not None:
            logger.info(f"Found package in repo")
            raise NotImplemented("TODO: Repo package source")
            return repo_pkg
        raise NotImplemented("TODO: Local file package source")
    return actions
