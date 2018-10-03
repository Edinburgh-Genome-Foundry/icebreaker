#!/usr/bin/env bash

docker exec -t docker_postgres_1 bash -lc 'pg_dump --username iceuser --format custom ice' > initial_state2.dmp