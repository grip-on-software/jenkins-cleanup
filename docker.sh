#!/bin/sh
docker ps -a -f status=exited -q | xargs --no-run-if-empty docker rm
docker images --filter dangling=false | grep "<none>" | awk  '{print $3}' | xargs --no-run-if-empty docker rmi
docker images -q --filter dangling=true | xargs --no-run-if-empty docker rmi
