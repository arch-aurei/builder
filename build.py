#!/usr/bin/env -S python -u

import csv
import os
import sys
import shutil
from tempfile import NamedTemporaryFile
from pathlib import Path
from typing import Optional
import pathlib

from jinja2 import Environment, PackageLoader, select_autoescape
from loguru import logger
from git import Repo

from arch import pkgbuild, resolver
from arch.repository import Repository
from arch.resolver import LocalInstall, AURInstall
from util import system
from util.s3repo import S3Repo

MANIFEST_NAME = "manifest.csv"
REPO_NAME = "aurei"
BUCKET_NAME = "aurei.nulls.ec"


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


def process_dependency(path, package):
    logger.debug("Checking package dependencies")
    makepkg_env = os.environ.copy()
    makepkg_env["PKGDEST"] = "../../artifacts"
    actions = resolver.resolve(package)
    for action in actions:
        if isinstance(action, LocalInstall):
            continue
        elif isinstance(action, AURInstall):
            logger.debug(f"Installing aur package: {action.package.name}")
            pkg_root = os.path.join(path, '../')
            Repo.clone_from(f'https://aur.archlinux.org/{action.package.name}.git',
                            os.path.join(pkg_root, action.package.name))
            pkg = pkgbuild.parse(os.path.join(pkg_root, action.package.name, 'PKGBUILD'))
            process_dependency(path, pkg)
            system.execute(['makepkg', '-s', '-i', '-C', '--noconfirm'], env=makepkg_env,
                           cwd=os.path.join(pkg_root, action.package.name))


def process(package: str, sha: str) -> None:
    logger.info(f"Processing package: {package}")
    m = Manifest(MANIFEST_NAME)
    manifest = m.check(package)
    if manifest is None or manifest != sha:
        logger.info(f"Building package {package}")
        makepkg_env = os.environ.copy()
        makepkg_env["PKGDEST"] = "../../artifacts"
        pkg = pkgbuild.parse(os.path.join(package, 'PKGBUILD'))
        process_dependency(package, pkg)
        system.execute(['makepkg', '-s', '-C', '--noconfirm'], env=makepkg_env, cwd=package)
        m.update(package, sha)
        logger.info(f"Package {package} updated")
    else:
        logger.info(f"Package {package} up to date, not rebuilding")


def build_main():
    logger.info("Building packages")
    system.update_packages()
    system.update_keys()

    repo = Repo(os.getcwd())
    for submodule in repo.iter_submodules():
        process(submodule.path, submodule.hexsha)


def package_main():
    packages = list(map(lambda x: os.path.basename(x), pathlib.Path('artifacts')
                        .glob('*.pkg.tar.zst')))
    logger.info(f"Found {len(packages)} packages to add to repo")
    if len(packages) > 0:
        system.import_key("aurei.pgp")
        repo = S3Repo(REPO_NAME, BUCKET_NAME)
        repo.download()
        for package in packages:
            repo.add_package(package)
        repo.upload()
        upload_index(repo)


def upload_index(repo):
    r = Repository(os.path.join("artifacts", f"{REPO_NAME}.db.tar.zst"))

    env = Environment(
        loader=PackageLoader('__main__', 'templates'),
        autoescape=select_autoescape(['html'])
    )
    template = env.get_template('index.html')
    with open(os.path.join('artifacts', 'index.html'), 'w') as writer:
        writer.write(template.render(packages=r.entries))
    repo.upload_file('index.html')


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
