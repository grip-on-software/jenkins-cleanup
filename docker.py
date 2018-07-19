"""
Script to clean up old tagged images from the local Docker graph.
"""

from __future__ import print_function
import argparse
import os.path
import sys
from datetime import datetime, timedelta
from gatherer.config import Configuration
from gatherer.domain.source import Source

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

class DockerTagCleanup(object):
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
            raise RuntimeError('Different registry URL: {}'.format(self.registry))

        if not name.startswith(self.group + '-'):
            raise RuntimeError('Does not belong to group {}'.format(self.group))

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
                print('{} on line {}'.format(error, line.strip()))

    def get_gitlab_projects(self, source):
        """
        Verify the repositories and branch sets for existence and return a set
        of tagged images that can be removed.
        """

        remove = set()
        gitlab_api = source.gitlab_api

        prefix = '{}/{}-'.format(self.registry, self.group)
        for repo, branches in self.check_repos.items():
            project = gitlab_api.projects.get('{}/{}'.format(self.group, repo))

            # List of existing branch names
            names = set(branch.name for branch in project.branches.list())
            removed = branches - names
            remove.update('{}{}:{}'.format(prefix, repo, branch) for branch in removed)

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
        print('Removing images {}'.format(', '.join(remove)))
        args.tags.write('\n'.join(remove))
    else:
        print('No images to remove')

if __name__ == '__main__':
    main()
