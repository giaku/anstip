#!/bin/bash

if [ ! -n "$1" ]; then
  echo "Prefix name as first arg is required to keep it tidy"
  exit
else
  PREFIX=$1
fi

podman build -t python-stress-test:v0.1 .
 
DATA_DIR=data
ERROR_LOG_DIR=error-logs
#PREFIX=newk8s-50rps
DATE_FORMAT=+%Y-%m-%d-%H:%M:%S

[ ! -d $DATA_DIR ] && mkdir $DATA_DIR
[ ! -d $DATA_DIR/$ERROR_LOG_DIR ] && mkdir $DATA_DIR/$ERROR_LOG_DIR

OUTPUT=$PREFIX-$(date $DATE_FORMAT)-latencies.csv
podman run python-stress-test:v0.1 2> $DATA_DIR/$ERROR_LOG_DIR/$PREFIX-$(date $DATE_FORMAT)-req-errors.txt 1> $DATA_DIR/$OUTPUT &

sleep 1
tail -f $DATA_DIR/$OUTPUT
