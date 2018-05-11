#!/bin/sh

LOGDIR=$1
STATSDIR=$2

set -e

for LOG in $(find $LOGDIR -name "*.log" -mmin +240); do
    echo "Rotating log $LOG"
    mv $LOG $LOG.rotated
done
if [[ $EUID -eq 0 ]]; then
    systemctl kill -s HUP --kill-who=main rsyslog.service
fi

for LOG in $(find $LOGDIR -name "*.log.rotated"); do
    echo "Processing log $LOG"
    ./update-stats.py --dest $STATSDIR $LOG
    xz $LOG
done
