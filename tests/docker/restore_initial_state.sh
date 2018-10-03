#!/usr/bin/env bash

docker exec -i docker_postgres_1 pg_restore --dbname=ice --username=iceuser --verbose --clean < backups/initial_state.dmp