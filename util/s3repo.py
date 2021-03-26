import os

import boto3
import mimetypes
from loguru import logger

from util import system


class S3Repo:
    def __init__(self, repo_name, bucket_name, compression="tar.zst", build_dir="artifacts"):
        self.repo_name = repo_name
        self.bucket_name = bucket_name
        self.compression = compression
        self.build_dir = build_dir
        self.repo_files = [str.join('.', [self.repo_name, 'db', compression]),
                           str.join('.', [self.repo_name, 'files', compression])]

        self.s3 = boto3.client('s3')

    def download(self):
        logger.info("Downloading repository files")
        for file in self.repo_files:
            self.s3.download_file(self.bucket_name, file, os.path.join(self.build_dir, file))

    def upload(self):
        logger.info("Uploading repository files")
        for file in self.repo_files:
            if file.endswith(f'.{self.compression}'):
                self.s3.upload_file(os.path.join(self.build_dir, file), self.bucket_name,
                                    file.replace(f'.{self.compression}', ''))
            self.upload_file(file)

    def upload_file(self, file):
        args = {}
        content_type = mimetypes.guess_type(file)[0]
        if content_type is not None:
            args['ContentType'] = content_type
        self.s3.upload_file(os.path.join(self.build_dir, file), self.bucket_name, file, ExtraArgs=args)

    def add_package(self, package):
        logger.info(f"Adding {package} to repository")
        self.upload_file(package)
        if os.path.isfile(f"{package}.sig"):
            logger.debug(f"Uploading signature")
            self.upload_file(f"{package}.sig")
        system.execute(["repo-add", str.join('.', [self.repo_name, 'db', self.compression]), package],
                       cwd=self.build_dir)
