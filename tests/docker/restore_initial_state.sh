#!/usr/bin/env bash

docker exec -i docker_postgres_1 pg_restore --no-owner -e --verbose --clean --no-acl --single-transaction --dbname=ice --username=iceuser /backups/initial_state.dmp