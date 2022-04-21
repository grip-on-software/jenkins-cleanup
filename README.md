# Jenkins, Docker and SonarQube cleanup

This repository contains maintenance scripts that perform cleanup of stale data 
in a Jenkins build server/node, a Docker registry and a SonarQube instance. 
Branch jobs for deleted branches, unused Docker container/images/tags and 
analysis projects for deleted branches are removed by the various scripts.

## Requirements

The Python scripts are based on the data gathering modules and require a proper 
installation of that package. If a PyPI registry is defined (possibly with 
a `PIP_REGISTRY` environment variable) and a proper installation location (such 
as a virtual environment) is known, it may be installed using `pip install -r 
requirements.txt`. The scripts also require configuration files that point to 
GitLab, Jenkins and Sonar instances as well as authentication for them. The 
configuration files may be pointed to using the `GATHERER_SETTINGS_FILE` and 
the `GATHERER_CREDENTIALS_FILE` environment variables, or provided within the 
working directory as `settings.cfg` and `credentials.cfg`, respectively. 
Documentation on adjusting the configuration within these files can be found in 
the `data-gathering` repository.

The cleanup scripts are assumed to be running on an agent with Docker installed 
(plus the usual shell scripting tools for Bash, grep and awk).

## Running

There are four scripts in this repository, three of which are Python-based:

- `jenkins.py`: Clean up old Jenkins multibranch pipeline jobs.
- `sonar.py`: Clean up old analysis projects from Sonar.
- `docker.py`: Find old tagged images to remove from the Docker graph.
- `docker.sh`: Remove specific Docker images (e.g. found by `docker.py`), or 
  remove exited containers, untagged images, dangling images, and list images 
  of the local Docker graph for further inspection (used by `docker.py`).

Some of the scripts have interactions with each other. This repository contains 
a `Jenkinsfile` with appropriate steps for a Jenkins CI deployment to regularly 
clean up a Jenkins agent.
