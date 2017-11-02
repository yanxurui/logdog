## inotify test
This tool requires inotify to work.
Here are some test cases on an Arch Linux(Linux version 4.11.7)


### watched file is renamed
```
watch a.txt

mv a.txt b.txt
MoveSELF /home/yanxurui/test/keepcoding/python/io/a.txt-unknown-path

echo bbb>>b.txt
Modify: /home/yanxurui/test/keepcoding/python/io/a.txt-unknown-path

mv b.txt a.txt
MoveSELF /home/yanxurui/test/keepcoding/python/io/a.txt-unknown-path
```

### watched file is moved to parent directory
```
watch a.txt

mv a.txt ../
MoveSELF /home/yanxurui/test/keepcoding/python/io/a.txt-unknown-path

mv ../a.txt ./
MoveSELF /home/yanxurui/test/keepcoding/python/io/a.txt-unknown-path
```

### watch a file repeatedly
```
watch a.txt
watch a.txt

echo aaa >> a.txt
Modify: /home/yanxurui/test/keepcoding/python/io/a.txt
```

### watch a file again after rm watch
```
watch a.txt
{'a.txt': 1}
mv a.txt ../
rm_watch 1
touch a.txt
add_watch a.txt
{'a.txt': 2}
```

### watch a file and its directory at the same time
```
touch a.txt
watch .
watch a.txt

echo aaa >> a.txt
Modify: /home/yanxurui/test/keepcoding/python/io/a.txt
Modify: /home/yanxurui/test/keepcoding/python/io/a.txt

mv a.txt b.txt
MoveFROM /home/yanxurui/test/keepcoding/python/io/a.txt
MoveTo /home/yanxurui/test/keepcoding/python/io/b.txt
MoveSELF /home/yanxurui/test/keepcoding/python/io/b.txt
```

### watch recursively
```
tree logs
logs
└── a
    └── a.txt

watch logs rec
{'logs': 1, 'logs/a': 2}

touch logs/a/b.txt
path=logs/a
```