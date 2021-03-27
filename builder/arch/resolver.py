import re
from enum import Enum
from typing import Protocol, Union

from loguru import logger

from builder.arch import repository_search
from builder.arch.pkgbuild import PkgBuildPackage
from builder.arch.repository import Repository, RepoPackage
from builder.arch.repository_search import LocalPackage, AURPackage

Package = Union[LocalPackage, AURPackage, RepoPackage, PkgBuildPackage]


# Find a packages dependencies
# Dependencies can either be:
# - in a local syncdb (core etc)
# - on the aur
# - in our local repo
# - part of a pkgbuild itself
def resolve(packages: list[str]) -> list[Package]:
    dependencies: list[Package] = []
    for pkg in packages:
        stripped_version = re.search(r"^([^<>=]+)", pkg)  # TODO: we should really check versions
        if stripped_version is not None:
            pkg = stripped_version.group(1)

        logger.info(f"Looking for dependency: {pkg}")
        local = repository_search.local_search(pkg)
        if local is not None:
            logger.info("Found package dependency locally")
            dependencies.append(local)
            continue
        remote = repository_search.aur_search(pkg)
        if remote is not None:
            logger.info("Found package on the AUR")
            dependencies.append(remote)
            continue
        repo = Repository("aurei")
        repo_pkg = repo.search(pkg)
        if repo_pkg is not None:
            logger.info("Found package in repo")
            raise NotImplementedError("TODO: Repo package source")
            # return repo_pkg
        raise NotImplementedError("TODO: Local file package source")
    return dependencies
