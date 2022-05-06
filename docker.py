"""
Script to clean up old tagged images from the local Docker graph.

Copyright 2017-2020 ICTU
Copyright 2017-2022 Leiden University

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from gatherer.config import Configuration
from gatherer.domain.source import Source
from gitlab.exceptions import GitlabGetError, GitlabListError

def parse_args():
    """
    Parse command line arguments.
    """

    config = Configuration.get_settings()

    description = "Remove old tagged images from the Docker graph"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--registry', default=os.getenv('DOCKER_REGISTRY'),
                        help='Registry URL')
    parser.add_argument('--group', default=None,
                        help="GitLab group in which the projects live")
    parser.add_argument('--gitlab', default=config.get('gitlab', 'url'),
                        help="GitLab URL")
    parser.add_argument("--days", type=int, default=2,
                        help="Number of days to keep old images")
    parser.add_argument("images", nargs='?', type=argparse.FileType('r'),
                        default=sys.stdin, help="List of candidate images")
    parser.add_argument("tags", nargs='?', type=argparse.FileType('w'),
                        default=sys.stdout, help="Output of tags to remove")
    return parser.parse_args()

class DockerTagCleanup:
    """
    Docker tag cleanup operations.
    """

    def __init__(self, registry='', group=None, days=''):
        self.check_repos = {}
        self.registry = registry
        self.group = group
        self.days = days

    def _parse_line(self, line):
        parts = line.strip().split(' ')
        if len(parts) != 3:
            raise RuntimeError('Too few parts')

        image, tag, date = parts
        if '/' not in image:
            raise RuntimeError('No docker registry image')

        registry, name = image.split('/', 1)
        if registry != self.registry:
            raise RuntimeError(f'Different registry URL: {self.registry}')

        if not name.startswith(self.group + '-'):
            raise RuntimeError(f'Does not belong to group {self.group}')

        repo = name[len(self.group + '-'):]
        offset = datetime.now() - timedelta(days=self.days)
        if offset < datetime.strptime(date, '%Y-%m-%d'):
            raise RuntimeError('Image is too recent')

        self.check_repos.setdefault(repo, set()).add(tag)

    def parse_image_projects(self, images_file):
        """
        Retrieve candidate images for removal and group them by repository
        name and branch sets.
        """

        self.check_repos = {}
        for line in images_file:
            try:
                self._parse_line(line.strip())
            except RuntimeError as error:
                print(f'{error} on line {line.strip()}')

    def get_gitlab_projects(self, source):
        """
        Verify the repositories and branch sets for existence and return a set
        of tagged images that can be removed.
        """

        remove = set()
        gitlab_api = source.gitlab_api

        prefix = f'{self.registry}/{self.group}-'
        for repo, branches in self.check_repos.items():
            project_name = f'{self.group}/{repo}'
            try:
                project = gitlab_api.projects.get(project_name)

                # List of existing branch names
                names = set(branch.name for branch in project.branches.list())
            except (GitlabGetError, GitlabListError) as error:
                print(f'{error} for GitLab project {project_name}')
                continue

            removed = branches - names
            remove.update(f'{prefix}{repo}:{branch}' for branch in removed)

        return remove

def main():
    """
    Main entry point.
    """

    args = parse_args()

    source = Source.from_type('gitlab', url=args.gitlab, name='GitLab')
    group = source.gitlab_group
    if group is None:
        group = args.group

    cleanup = DockerTagCleanup(args.registry, group, args.days)
    cleanup.parse_image_projects(args.images)
    remove = cleanup.get_gitlab_projects(source)

    if remove:
        print(f"Removing images {', '.join(remove)}")
        args.tags.write('\n'.join(remove))
    else:
        print('No images to remove')

if __name__ == '__main__':
    main()
