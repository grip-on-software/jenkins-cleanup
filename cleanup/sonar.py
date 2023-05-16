"""
Script to clean up old analysis projects from Sonar.

Copyright 2017-2020 ICTU
Copyright 2017-2022 Leiden University
Copyright 2017-2023 Leon Helwerda

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

from argparse import ArgumentParser, Namespace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Set
from gatherer.config import Configuration
from gatherer.domain.source.gitlab import GitLab
from gatherer.request import Session
from gitlab.exceptions import GitlabGetError, GitlabListError
from requests.auth import HTTPBasicAuth

def parse_args() -> Namespace:
    """
    Parse command line arguments.
    """

    config = Configuration.get_settings()
    verify = config.get('sonar', 'verify')
    if not Configuration.has_value(verify):
        verify = False
    elif not Path(verify).exists():
        verify = True

    description = "Remove old branch analysis projects from Sonar"
    parser = ArgumentParser(description=description)
    parser.add_argument('--url', help='Sonar URL',
                        default=config.get('sonar', 'host'))
    parser.add_argument('--username', help='Sonar username',
                        default=config.get('sonar', 'username'))
    parser.add_argument('--password', help='Sonar password',
                        default=config.get('sonar', 'password'))
    parser.add_argument('--verify', nargs='?', const=True, default=verify,
                        help='Enable SSL certificate verification')
    parser.add_argument('--no-verify', action='store_false', dest='verify',
                        help='Disable SSL certificate verification')
    parser.add_argument('--group', default=None,
                        help="GitLab group in which the projects live")
    parser.add_argument('--gitlab', default=config.get('gitlab', 'url'),
                        help="GitLab URL")
    parser.add_argument("--days", type=int, default=2,
                        help="Number of days to keep old projects")
    return parser.parse_args()

def get_sonar_projects(session: Session, url: str, days: int = 2) -> \
        Dict[str, Set[str]]:
    """
    Retrieve candidate Sonar projects for removal and group them by repository
    name and branch sets.
    """

    offset = datetime.now().replace(microsecond=0) - timedelta(days=days)
    url = f"{url}/api/projects/search?analysisBefore={offset.isoformat()}"

    request = session.get(url)
    request.raise_for_status()
    try:
        projects = request.json()
    except ValueError as error:
        raise ValueError(f'Invalid JSON response: {request.text}') from error

    check_repos: Dict[str, Set[str]] = {}
    for project in projects['components']:
        # Only consider projects with branches
        key = str(project['key'])
        if ':' in key:
            repo, branch = key.split(':')
            check_repos.setdefault(repo, set()).add(branch)

    return check_repos

def get_gitlab_projects(check_repos: Dict[str, Set[str]], args: Namespace) -> \
        Set[str]:
    """
    Verify the repositories and branch sets for existence and return a set
    of Sonar projects that can be removed.
    """

    remove: Set[str] = set()
    source = GitLab('gitlab', url=args.gitlab, name='GitLab')
    gitlab_api = source.gitlab_api
    group = source.gitlab_group
    if group is None:
        group = str(args.group)

    for repo, branches in check_repos.items():
        project_name = f'{group}/{repo}'
        try:
            project = gitlab_api.projects.get(project_name)

            # List of existing branch names
            names = set(str(branch.name) for branch in project.branches.list())
        except (GitlabGetError, GitlabListError) as error:
            print(f'{error} for GitLab project {project_name}')
            continue

        removed = branches - names
        remove.update(f'{repo}:{branch}' for branch in removed)

    return remove

def main() -> None:
    """
    Main entry point.
    """

    args = parse_args()

    auth = HTTPBasicAuth(args.username, args.password)
    session = Session(verify=args.verify, auth=auth)
    sonar_url = str(args.url).rstrip('/')

    check_repos = get_sonar_projects(session, sonar_url, args.days)
    remove = get_gitlab_projects(check_repos, args)

    if remove:
        print(f"Removing Sonar projects {', '.join(remove)}")
        request = session.post(f'{sonar_url}/api/projects/bulk_delete',
                               data={'projects': ','.join(remove)})
        request.raise_for_status()
    else:
        print('No Sonar projects to remove')

if __name__ == '__main__':
    main()
