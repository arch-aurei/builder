#!/usr/bin/env -S python -u

import csv
import os
import sys
import shutil
import io
from tempfile import NamedTemporaryFile
from subprocess import Popen, PIPE
from pathlib import Path
from typing import Optional
from threading import Thread
from io import StringIO
import pathlib

from loguru import logger
import boto3

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
        logger.debug(f"Checking {row['package']} ~ {package}")
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


class System:
  @staticmethod
  def update_packages():
    logger.info("Updating system packages")
    System.execute(['sudo', 'pacman', '-Syu', '--noconfirm'])

  @staticmethod
  def update_keys():
    logger.info("Updating system keyring")
    with open('keys.txt', 'r') as keys:
      for key in keys.read().split("\n"):
        if key.strip() != "":
          keypart = key.split('#')[0].strip()
          System.execute(['gpg', '--recv-key', keypart])

  @staticmethod
  def tee(infile, *files):
    def fanout(infile, *files):
      with infile:
        for line in iter(infile.readline, ""):
          for f in files:
            if isinstance(f, io.TextIOBase):
              f.write(str(line))
            elif callable(f):
              f(str(line).strip())
            else:
              f.write(bytes(line, 'utf-8'))
              f.flush()
    t = Thread(target=fanout, args=(infile,) + files)
    t.daemon = True
    t.start()
    return t

  @staticmethod
  def execute(command, cwd=None, env=None):
    logger.debug(f"executing command: {command}")
    p = Popen(command, stdout=PIPE, stderr=PIPE, cwd=cwd, env=env, text=True)
    stout = StringIO()
    sterr = StringIO()
    threads = [System.tee(p.stdout, stout, logger.debug), System.tee(p.stderr, sterr, logger.error)]
    for t in threads:
      t.join()
    ret = p.wait()
    if ret != 0:
      logger.error(f"failed to execute command: {command} exit code {ret}")
      exit(100)
    stout.seek(0)
    return stout.read()


def process(package: str, sha: str) -> None:
  logger.info(f"Processing package: {package}")
  m = Manifest(MANIFEST_NAME)
  manifest = m.check(package)
  if manifest is None or manifest != sha:
    logger.info(f"Building package {package}")
    makepkg_env = os.environ.copy()
    makepkg_env["PKGDEST"] = "../../artifacts"
    System.execute(['makepkg', '-s', '-C', '--noconfirm'], env=makepkg_env, cwd=package)
    m.update(package, sha)
    logger.info(f"Package {package} updated")
  else:
    logger.info(f"Package {package} up to date, not rebuilding")


def build_main():
  logger.info("Building packages")
  System.update_packages()
  System.update_keys()

  packages = System.execute(['git', 'submodule', 'status'])
  for line in packages.split("\n"):
    if line.strip() != "":
      xs = line.strip().split(" ")
      process(xs[1], xs[0])


class Repo:
  def __init__(self, repo_name):
    self.repo_name = repo_name
    self.s3 = boto3.client('s3')
    self.repo_files = [f"{self.repo_name}.db.tar.zst", f"{self.repo_name}.files.tar.zst"]

  def download(self):
    logger.info("Downloading repository files")
    for file in self.repo_files:
      self.s3.download_file(BUCKET_NAME, file, f"artifacts/{file}")

  def upload(self):
    logger.info("Uploading repository files")
    for file in self.repo_files:
      if file.endswith('.tar.zst'):
        self.s3.upload_file(f"artifacts/{file}", BUCKET_NAME, file.replace('.tar.zst', ''))
      self.s3.upload_file(f"artifacts/{file}", BUCKET_NAME, file)

  def add_package(self, package):
    logger.info(f"Adding {package} to repository")
    self.s3.upload_file(f"artifacts/{package}", BUCKET_NAME, package)
    System.execute(["repo-add", f"{self.repo_name}.db.tar.zst", package], cwd="artifacts")


def package_main():
  packages = list(map(lambda x: os.path.basename(x), pathlib.Path('artifacts').glob('*.pkg.tar.zst')))
  logger.info(f"Found {len(packages)} packages to add to repo")
  if len(packages) > 0:
    repo = Repo(REPO_NAME)
    repo.download()
    for package in packages:
      repo.add_package(package)
    repo.upload()


if __name__ == "__main__":
  logger.remove(0)
  logger.add(sys.stderr, format="<level>{level: <8}</level> | <cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>", colorize=True)
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument('--build', help='build latest packages',
                      action='store_true')
  parser.add_argument('--package', help='update repo with latest packages',
                      action='store_true')
  args = parser.parse_args()
  if args.build and args.package:
    print("Cowardly refusing to do both build and package")
    exit(-1)
  elif (not args.build) and (not args.package):
    parser.print_help()
    exit(-1)

  if args.build:
    build_main()
  elif args.package:
    package_main()
