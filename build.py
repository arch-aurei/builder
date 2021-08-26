#!/usr/bin/env -S python -u

import csv
import json
import os
import pathlib
import shutil
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

from git import Repo
from loguru import logger

from builder.arch import resolver, pkgbuild
from builder.arch.pkgbuild import PkgBuildPackage
from builder.arch.repository import Repository
from builder.arch.repository_search import LocalPackage, AURPackage
from builder.arch.resolver import Package
from builder.util import system
from builder.util.s3repo import S3Repo

MANIFEST_NAME = "manifest.csv"
REPO_NAME = "aurei"
BUCKET_NAME = "aurei.nulls.ec"
KEY_NAME = "aurei.pgp"
KEY_ID = "565ABC3363CDD9F1E333E5744AAFA429C6F28921"
MAX_PER_BUILD = 5


class Manifest:
    """ Manifest file of latest package updates """
    HEADER = ['package', 'sha']

    def __init__(self, filename: str):
        self.filename = filename
        Path(self.filename).touch()

    def check(self, package: str) -> Optional[str]:
        with open(self.filename, 'r') as manifest:
            reader = csv.DictReader(manifest, Manifest.HEADER)
            for row in reader:
                if row['package'].lower() == package.lower():
                    return row['sha']
            return None

    def update(self, package: str, sha: str) -> None:
        tempfile = NamedTemporaryFile(mode='w', delete=False)
        with open(self.filename, 'r') as manifest, tempfile:
            reader = csv.DictReader(manifest, fieldnames=Manifest.HEADER)
            writer = csv.DictWriter(tempfile, fieldnames=Manifest.HEADER)
            found = False
            for row in reader:
                if row['package'] == package:
                    found = True
                    row['sha'] = sha
                writer.writerow({'package': row['package'], 'sha': row['sha']})
            if not found:
                writer.writerow({'package': package, 'sha': sha})

        shutil.move(tempfile.name, self.filename)


def makepkg_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PKGDEST"] = "../../artifacts"
    env["PATH"] = "/usr/local/bin:/usr/local/sbin:/usr/bin"
    return env


def process_dependency(path: str, package: Package, env_packages: list[PkgBuildPackage]) -> None:
    logger.debug("Checking package dependencies")
    dependencies = resolver.resolve(list(map(lambda x: x["name"], package.depends)), env_packages)
    for dependency in dependencies:
        if isinstance(dependency, LocalPackage):
            continue
        elif isinstance(dependency, AURPackage):
            logger.debug(f"Installing aur package: {dependency.name} (from {dependency.package_base}")
            pkg_root = os.path.join(path, '../')
            target_repo = os.path.join(pkg_root, dependency.name)
            if os.path.exists(path=target_repo):
                # Already done as part of this run? try re-clone
                shutil.rmtree(target_repo)

            Repo.clone_from(f'https://aur.archlinux.org/{dependency.package_base}.git', target_repo)
            pkgs = pkgbuild.parse(target_repo)
            for pkg in pkgs:
                if pkg.name == dependency.name or pkg.name == dependency.package_base:
                    continue
                process_dependency(path, pkg, env_packages)
            system.execute(['makepkg', '-s', '-i', '-C', '--noconfirm'], env=makepkg_env(),
                           cwd=target_repo)


def process(package: str, sha: str) -> bool:
    logger.info(f"Processing package: {package}")
    m = Manifest(MANIFEST_NAME)
    manifest = m.check(package)
    if manifest is None or manifest != sha:
        logger.info(f"Building package {package}")
        pkgs = pkgbuild.parse(package)
        for pkg in pkgs:
            process_dependency(package, pkg, pkgs)
        system.execute(['makepkg', '-s', '-C', '--noconfirm'], env=makepkg_env(), cwd=package)
        m.update(package, sha)
        logger.info(f"Package {package} updated")
        return True
    else:
        logger.info(f"Package {package} up to date, not rebuilding")
        return False


def build_main() -> None:
    logger.info("Building packages")
    system.update_packages()
    system.update_keys()
    system.import_key(KEY_NAME, KEY_ID)

    repo = Repo(os.getcwd())
    builds = 0
    for submodule in repo.iter_submodules():
        if process(submodule.path, submodule.hexsha):
            builds += 1
        if builds >= MAX_PER_BUILD:
            logger.info("Hit max builds per single run, please run again")
            exit(0)


def package_main() -> None:
    packages = list(filter(lambda x: not x.endswith(".sig"),
                           map(lambda x: os.path.basename(x),
                               pathlib.Path('artifacts').glob('*.pkg.tar*'))))
    logger.info(f"Found {len(packages)} packages to add to repo")
    if len(packages) > 0:
        system.import_key(KEY_NAME, KEY_ID)
        repo = S3Repo(REPO_NAME, BUCKET_NAME)
        repo.download()
        for package in packages:
            repo.add_package(package)
        repo.upload()
        upload_index(repo)


def upload_index(repo: S3Repo) -> None:
    r = Repository(os.path.join("artifacts", f"{REPO_NAME}.db.tar.zst"))

    with open(os.path.join('artifacts', 'repoPackages.json'), 'w') as writer:
        vs = list(map(lambda v: v.dict(), r.entries.values()))
        writer.write(json.dumps(vs))
    repo.upload_file('repoPackages.json')


def render_main():
    repo = S3Repo(REPO_NAME, BUCKET_NAME)
    repo.download()
    upload_index(repo)


if __name__ == "__main__":
    logger.remove(0)
    logger.add(sys.stderr,
               format="<level>{level: <8}</level> | <cyan>{function}</cyan>:"
                      "<cyan>{line}</cyan> - <level>{message}</level>",
               colorize=True)
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--build', help='build latest packages',
                        action='store_true')
    parser.add_argument('--package', help='update repo with latest packages',
                        action='store_true')
    parser.add_argument('--render', help='render and upload an index.html for the repo',
                        action='store_true')
    args = parser.parse_args()
    if args.build and args.package:
        print("Cowardly refusing to do both build and package")
        exit(-1)
    elif (not args.build) and (not args.package) and (not args.render):
        parser.print_help()
        exit(-1)

    if args.build:
        build_main()
    elif args.package:
        package_main()
    elif args.render:
        render_main()
