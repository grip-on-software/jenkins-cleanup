#!/bin/sh

if [ ! -z "$1" ]; then
	cat "$1" | xargs --no-run-if-empty docker rmi
else
	docker ps -a -f status=exited -q | xargs --no-run-if-empty docker rm
	docker images --filter dangling=false | grep "<none>" | awk  '{print $3}' | xargs --no-run-if-empty docker rmi
	docker images -q --filter dangling=true | xargs --no-run-if-empty docker rmi
	docker images --format "{{.Repository}} {{.Tag}} {{.CreatedAt}}" --filter dangling=false | grep -Ev "\s(<none>|latest|[0-9]+\.[0-9]+\.[0-9]+)\s" | grep "^docker-registry" | awk '{print $1, $2, $3}' > images.txt
fi
