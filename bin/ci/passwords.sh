#!/usr/bin/env bash
docker ps --format '{{.Names}} {{.Label "PASSWORD"}}'