"""
Script to clean up old analysis projects from Sonar.
"""

import argparse
import os.path
from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth
from gatherer.config import Configuration
from gatherer.domain.source import Source
from gatherer.request import Session
from gitlab.exceptions import GitlabGetError, GitlabListError

def parse_args():
    """
    Parse command line arguments.
    """

    config = Configuration.get_settings()
    verify = config.get('sonar', 'verify')
    if not Configuration.has_value(verify):
        verify = False
    elif not os.path.exists(verify):
        verify = True

    description = "Remove old branch analysis projects from Sonar"
    parser = argparse.ArgumentParser(description=description)
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

def get_sonar_projects(session, url, days=2):
    """
    Retrieve candidate Sonar projects for removal and group them by repository
    name and branch sets.
    """

    offset = datetime.now().replace(microsecond=0) - timedelta(days=days)
    url = "{}/api/projects/search?analysisBefore={}".format(url,
                                                            offset.isoformat())

    request = session.get(url)
    request.raise_for_status()
    try:
        projects = request.json()
    except ValueError:
        raise ValueError('Invalid JSON response: {}'.format(request.text))

    check_repos = {}
    for project in projects['components']:
        # Only consider projects with branches
        key = project['key']
        if ':' in key:
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
        project_name = '{}/{}'.format(group, repo)
        try:
            project = gitlab_api.projects.get(project_name)

            # List of existing branch names
            names = set(branch.name for branch in project.branches.list())
        except (GitlabGetError, GitlabListError) as error:
            print('{} for GitLab project {}'.format(error, project_name))
            continue

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

    if remove:
        print('Removing Sonar projects {}'.format(', '.join(remove)))
        request = session.post('{}/api/projects/bulk_delete'.format(sonar_url),
                               data={'projects': ','.join(remove)})
        request.raise_for_status()
    else:
        print('No Sonar projects to remove')

if __name__ == '__main__':
    main()
