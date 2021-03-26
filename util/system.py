import io
import os
from subprocess import Popen, PIPE
from threading import Thread
from io import StringIO

from loguru import logger


def update_packages():
    logger.info("Updating system packages")
    execute(['sudo', 'pacman', '-Syu', '--noconfirm'])


def update_keys():
    if os.path.isfile('keys.txt'):
        logger.info("Updating system keyring")
        with open('keys.txt', 'r') as keys:
            for key in keys.read().split("\n"):
                if key.strip() != "":
                    keypart = key.split('#')[0].strip()
                    execute(['gpg', '--recv-key', keypart])


def import_key(name: str, keyid: str):
    if os.path.isfile(name):
        logger.info("Importing signing key")
        execute(['gpg', '--import', name])
        execute(['sudo', 'pacman-key', '--init'])
        execute(['sudo', 'pacman-key', '--populate'])
        execute(['sudo', 'pacman-key', '--add', name.replace('pgp', 'asc')])
        execute(['sudo', 'pacman-key', '--lsign', keyid])


def _tee(infile, *files):
    def fanout(infile_, *files_):
        with infile_:
            for line in iter(infile_.readline, ""):
                for file in files_:
                    if isinstance(file, io.TextIOBase):
                        file.write(str(line))
                    elif callable(file):
                        file(str(line).strip())
                    else:
                        file.write(bytes(line, 'utf-8'))
                        file.flush()

    t = Thread(target=fanout, args=(infile,) + files)
    t.daemon = True
    t.start()
    return t


def execute(command, cwd=None, env=None):
    logger.debug(f"executing command: {command}")
    p = Popen(command, stdout=PIPE, stderr=PIPE, cwd=cwd, env=env, text=True)
    stout = StringIO()
    sterr = StringIO()
    threads = [_tee(p.stdout, stout, logger.debug), _tee(p.stderr, sterr, logger.error)]
    for t in threads:
        t.join()
    ret = p.wait()
    if ret != 0:
        logger.error(f"failed to execute command: {command} exit code {ret}")
        exit(100)
    stout.seek(0)
    return stout.read()
