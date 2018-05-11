#!/bin/sh

rm -rf test-data-live test-stats a.json b.json
cp -Ra test-data test-data-live

echo "FIRST TEST RUN"
echo "=============="
./process-logs.sh `pwd`/test-data-live `pwd`/test-stats
json_pp -json_opt pretty,canonical < test-stats/2018/5/8.json > a.json
tree test-stats

echo "SECOND TEST RUN"
echo "==============="
./process-logs.sh `pwd`/test-data-live `pwd`/test-stats
tree test-stats

echo "THIRD TEST RUN"
echo "=============="
cp -Ra test-data/2018/05/08/199.27.72.20.log test-data-live/2018/05/08/199.27.72.21.log
./process-logs.sh `pwd`/test-data-live `pwd`/test-stats
json_pp -json_opt pretty,canonical < test-stats/2018/5/8.json > b.json
tree test-stats
diff -u a.json b.json

rm -rf test-data-live test-stats a.json b.json
