import re

from loguru import logger

from arch import repository_search
from arch.repository import Repository
from arch.repository_item import RepositoryItem


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
        stripped_version = re.search(r"^([^<>=]+)", pkg) # TODO: we should really check versions
        pkg = stripped_version.group(1)

        logger.info(f"Looking for dependency: {pkg}")
        local = repository_search.local_search(pkg)
        if local is not None:
            logger.info("Found package dependency locally")
            actions.append(LocalInstall(local))
            continue
        remote = repository_search.aur_search(pkg)
        if remote is not None:
            logger.info("Found package on the AUR")
            actions.append(AURInstall(remote))
            continue
        repo = Repository("aurei")
        repo_pkg = repo.search(package)
        if repo_pkg is not None:
            logger.info("Found package in repo")
            raise NotImplementedError("TODO: Repo package source")
            # return repo_pkg
        raise NotImplementedError("TODO: Local file package source")
    return actions
