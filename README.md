# virsh-qemu-guest-agent-execute-command
A python tool to run a command in a VM with virsh and qemu-guest-agent

When reading from stdin, the command does not run until all the input has been read and can be transferred to the guest agent.

```sh
$ ./run-command.py foo whoami
root

$ ./run-command.py foo ip a
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
...

$ ./run-command.py foo -e FOO=BAR env
FOO=BAR

$ echo error | ./run-command.py foo - cat
error

$ ./run-command.py foo -i "error" cat
error

$ ./run-command.py foo -- bash -c "echo foo >&2"
foo
```

```
Usage:
  ./run_command.py <vmname> [-i TEXT | - ]  [-e VAREQVALUE]... [--] <program> [<args>...]

-i TEXT, --input TEXT                  The text sent on stdin.
-                                      If set, input is read from stdin.
-e VAREQVALUE, --env VAREQVALUE        Pairs VAR=VALUE for environment variables
```
