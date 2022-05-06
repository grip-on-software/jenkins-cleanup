#!/bin/sh

# Clean up Docker graph.
#
# Either remove specific Docker images (e.g. found by `docker.py`), or remove
# exited containers, untagged images, dangling images, and list images of the
# local Docker graph for further inspection (used by `docker.py`).
#
# Copyright 2017-2020 ICTU
# Copyright 2017-2022 Leiden University
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

if [ ! -z "$1" ]; then
	cat "$1" | xargs --no-run-if-empty docker rmi
else
	docker ps -a -f status=exited -q | xargs --no-run-if-empty docker rm
	docker images --filter dangling=false | grep "<none>" | awk  '{print $3}' | xargs --no-run-if-empty docker rmi
	docker images -q --filter dangling=true | xargs --no-run-if-empty docker rmi
	docker images --format "{{.Repository}} {{.Tag}} {{.CreatedAt}}" --filter dangling=false | grep -Ev "\s(<none>|latest|[0-9]+\.[0-9]+\.[0-9]+)\s" | grep "^$DOCKER_REGISTRY" | awk '{print $1, $2, $3}' > images.txt
fi
