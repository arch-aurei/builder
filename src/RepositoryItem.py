from dataclasses import dataclass
from typing import Optional


@dataclass
class RepositoryItem:
    """ Represents a package in a repository, this is the minimum across local, aur and repo """
    filename: Optional[str]
    name: str
    base: Optional[str]
    version: str
    desc: str
    csize: Optional[int]
    isize: Optional[int]
    md5sum: Optional[str]
    sha256sum: Optional[str]
    url: str
    license: [str]
    arch: Optional[str]
    builddate: Optional[str]
    packager: Optional[str]
    depends: [str]
    optdepends: [str]
    makedepends: [str]
