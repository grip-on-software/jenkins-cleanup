"""
Script to clean up old Jenkins multibranch pipeline jobs.
"""

import argparse
from datetime import datetime, timedelta
from gatherer.config import Configuration
from gatherer.jenkins import Jenkins

def parse_args():
    """
    Parse command line arguments.
    """

    description = "Remove old branch jobs"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--days", type=int, default=2,
                        help="Number of days to keep old jobs")
    return parser.parse_args()

def main():
    """
    Main entry point.
    """

    args = parse_args()
    config = Configuration.get_settings()
    jenkins = Jenkins.from_config(config)

    offset = datetime.now() - timedelta(days=args.days)
    for job in jenkins.jobs:
        # Never remove the only job of a multibranch pipeline workflow
        if len(job.jobs) > 1:
            for branch in job.jobs:
                if not branch.data['buildable']:
                    build = branch.last_build
                    last = datetime.fromtimestamp(build.data['timestamp'] / 1000)
                    if last < offset:
                        print("Removing old branch {}/{}".format(job.name,
                                                                 branch.name))
                        branch.delete()

if __name__ == '__main__':
    main()
