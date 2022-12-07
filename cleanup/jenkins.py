"""
Script to clean up old Jenkins multibranch pipeline jobs.

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

from argparse import ArgumentParser, Namespace
from datetime import datetime, timedelta
from gatherer.config import Configuration
from gatherer.jenkins import Jenkins

def parse_args() -> Namespace:
    """
    Parse command line arguments.
    """

    description = "Remove old branch jobs"
    parser = ArgumentParser(description=description)
    parser.add_argument("--days", type=int, default=2,
                        help="Number of days to keep old jobs")
    return parser.parse_args()

def main() -> None:
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
                        print(f"Removing old branch {job.name}/{branch.name}")
                        branch.delete()

if __name__ == '__main__':
    main()
