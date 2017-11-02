#!/usr/bin/env bash

num=100000

echo "write $num lines into the log file"

# How to flush output of Python print: https://stackoverflow.com/a/230780/6088837
cmd='python2.7 -u ../src/logdog.py -c ../conf.py'
pid=$(pgrep -f "$cmd" -d' ')
if [ $? -eq 0 ]; then
    echo -n stop...
    echo $pid
    kill -s SIGINT $pid
    sleep 1
fi
rm a.log
rm logdog.log
rm /tmp/logdog.*
touch a.log b.log
mkdir -p logs
echo start...
echo $cmd
$cmd

for i in $(seq $num);do
    echo "wrong $i" >> a.log
done

sleep 5
if [ -s /tmp/logdog.err ];then
    cat /tmp/logdog.err
    exit 1
fi

wc -l /tmp/logdog.out
diff /tmp/logdog.out a.log
tail -1 logdog.log | grep -v $num
