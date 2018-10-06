#!/usr/bin/env bash

docker exec -i docker_postgres_1 pg_restore --no-owner --verbose --clean --no-acl --dbname=ice --username=iceuser /backups/initial_state.dmp