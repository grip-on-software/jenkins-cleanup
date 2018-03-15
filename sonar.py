"""
Script to clean up old analysis projects from Sonar.
"""

import argparse
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
from gatherer.config import Configuration
from gatherer.domain.source import Source
from gatherer.request import Session

def parse_args():
    """
    Parse command line arguments.
    """

    config = Configuration.get_settings()

    description = "Remove old branch analysis projects from Sonar"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--url', help='Sonar URL',
                        default=config.get('sonar', 'host'))
    parser.add_argument('--username', help='Sonar username',
                        default=config.get('sonar', 'username'))
    parser.add_argument('--password', help='Sonar password',
                        default=config.get('sonar', 'password'))
    parser.add_argument('--verify', nargs='?', const=True, default=False,
                        help="Enable SSL certificate verification")
    parser.add_argument('--group', default=None,
                        help="GitLab group in which the projects live")
    parser.add_argument('--gitlab', default=config.get('gitlab', 'url'),
                        help="GitLab URL")
    parser.add_argument("--days", type=int, default=2,
                        help="Number of days to keep old projects")
    return parser.parse_args()

def get_sonar_projects(session, url, days=2):
    """
    Retrieve candidate Sonar projects for removal and group them by repository
    name and branch sets.
    """

    offset = datetime.now().replace(microsecond=0) - timedelta(days=days)
    url = "{}/api/projects/search?analysisBefore={}".format(url,
                                                            offset.isoformat())
    print(url)

    request = session.get(url)
    request.raise_for_status()
    try:
        projects = request.json()
    except ValueError:
        raise ValueError('Invalid JSON response: {}'.format(request.text))

    check_repos = {}
    for project in projects['components']:
        key = project['key']
        repo, branch = key.split(':')
        check_repos.setdefault(repo, set()).add(branch)

    return check_repos

def get_gitlab_projects(check_repos, args):
    """
    Verify the repositories and branch sets for existence and return a set
    of Sonar projects that can be removed.
    """

    remove = set()
    source = Source.from_type('gitlab', url=args.gitlab, name='GitLab')
    gitlab_api = source.gitlab_api
    group = source.gitlab_group
    if group is None:
        group = args.group

    for repo, branches in check_repos.items():
        project = gitlab_api.project('{}/{}'.format(group, repo))
        existing = project.branches()

        names = set(branch.name for branch in existing)
        removed = branches - names
        remove.update('{}:{}'.format(repo, branch) for branch in removed)

    return remove

def main():
    """
    Main entry point.
    """

    args = parse_args()

    auth = HTTPBasicAuth(args.username, args.password)
    session = Session(verify=args.verify, auth=auth)
    sonar_url = args.url.rstrip('/')

    check_repos = get_sonar_projects(session, sonar_url, args.days)
    remove = get_gitlab_projects(check_repos, args)

    print('Removing projects {}'.format(', '.join(remove)))
    request = session.post('{}/api/projects/bulk_delete'.format(sonar_url),
                           data={'projects': ','.join(remove)})
    request.raise_for_status()

if __name__ == '__main__':
    main()
