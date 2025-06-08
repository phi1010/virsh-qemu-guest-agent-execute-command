#!/usr/bin/env python3
"""
Usage:
  {0} <vmname> [-i TEXT | - ]  [-e VAREQVALUE]... [--] <program> [<args>...]

-i TEXT, --input TEXT                  The text sent on stdin.
-                                      If set, input is read from stdin.
-e VAREQVALUE, --env VAREQVALUE        Pairs VAR=VALUE for environment variables
"""
__doc__ = __doc__.format(__file__)

import os
import sys
import base64
from time import sleep
from docopt import docopt
from pymaybe import maybe
# noinspection PyUnresolvedReferences
from sh import virsh
from json import dumps, loads
from icecream import ic
from easydict import EasyDict as edict

def run(args):
    program = args["<program>"]
    vmname = args["<vmname>"]
    can_exec = check_can_exec(vmname)
    if not can_exec:
        print("Error, guest agent does not support the exec command")
        sys.exit(1)
    if program is not None:
        env = args["--env"]
        input = args["--input"]
        if args["-"]:
            input = sys.stdin.read()
        args = args["<args>"]
        stdout, stderr, exitcode = exec_shell_command(vmname, program=program, args=args, input_data=input, env=env)
        print(stdout, file=sys.stdout, end="")
        print(stderr,file=sys.stderr, end="")
        sys.exit(exitcode)


def check_can_exec(vmname):
    supported_commands = get_supported_commands(vmname)
    can_exec = "guest-exec" in supported_commands and "guest-exec-status" in supported_commands
    return can_exec


def get_supported_commands(vmname):
    supported_commands = guest_info(vmname).get("return", {}).get("supported_commands", [])
    supported_commands = [command["name"] for command in supported_commands if command["enabled"]]
    return supported_commands


def test(vmname):
    # https://qemu-project.gitlab.io/qemu/interop/qemu-ga-ref.html#qapidoc-199
    # guest-exec Command

    ic(exec_shell_command(vmname, "env", [], "", ["FOO=BAR"]))
    ic(exec_shell_command(vmname, "uname", ["-a"]))
    ic(exec_shell_command(vmname, "cat", input_data="foo"))
    ic(exec_shell_command(vmname, "bash", ["-c", "cat>&2"], input_data="foo"))
    ic(exec_shell_command(vmname, "whoami", ))
    ic(exec_shell_command(vmname, "id", ))
    # ic(exec_shell_command(vmname, "sleep",["1"]))
    # ic(exec_shell_command(vmname, "sleep",["2"]))
    # ic(exec_shell_command(vmname, "sleep",["3"]))
    # ic(exec_shell_command(vmname, "systemctl"))
    ic(exec_shell_command(vmname, "who"))
    print(exec_shell_command(vmname, "ip", ["a"])[0])


def exec_shell_command(vmname: str, program: str, args: list[str] = None, input_data: str = None, env: list[str] = None):
    if input_data is None:
        input_data = ""
    if env is None:
        env = []
    if args is None:
        args = []

    if isinstance(env, dict):
        env = [f"{key}={value}" for key, value in env.items()]

    qemu_reply = exec_command(vmname, dict(execute="guest-exec", arguments={
        'path': program,
        "capture-output": True,
        "input-data": base64.encodebytes(input_data.encode()).decode(),
        "env": env,
        "arg": args,
    }))
    # https://qemu-project.gitlab.io/qemu/interop/qemu-ga-ref.html#qapidoc-195
    # GuestExec Object
    pid = qemu_reply["return"]["pid"]
    # ic(qemu_reply)
    # https://qemu-project.gitlab.io/qemu/interop/qemu-ga-ref.html#qapidoc-195
    # guest-exec-status Command
    while True:
        qemu_reply = exec_command(vmname, dict(execute="guest-exec-status", arguments={'pid': pid}))
        exited: bool = qemu_reply["return"]["exited"]
        # ic(exited)
        if exited:
            # ic(qemu_reply)
            exitcode: int = maybe(qemu_reply)["return"]["exitcode"].or_else(None)
            signal: int = maybe(qemu_reply)["return"]["signal"].or_else(None)
            stdout: str = base64.decodebytes(maybe(qemu_reply)["return"]["out-data"].encode().or_else(b"")).decode()
            stderr: str = base64.decodebytes(maybe(qemu_reply)["return"]["err-data"].encode().or_else(b"")).decode()
            stdout_trunc: bool = maybe(qemu_reply)["return"]["out-truncated"].or_else(False)
            stderr_trunc: bool = maybe(qemu_reply)["return"]["err-truncated"].or_else(False)
            # ic(exited, exitcode, signal, stdout, stderr, stdout_trunc, stderr_trunc)
            return stdout, stderr, exitcode
            # break
        sleep(0.05)


def exec_command(vmname, json):
    """
    Provide a matching json, as in https://qemu-project.gitlab.io/qemu/interop/qemu-qmp-ref.html#qapidoc-133 :
        -> { "execute": "set-action",
             "arguments": { "reboot": "shutdown",
                            "shutdown" : "pause",
                            "panic": "pause",
                            "watchdog": "inject-nmi" } }
        <- { "return": {} }
    """
    command = dumps(json)
    response = virsh("qemu-agent-command", vmname, command)
    # ic(response.__dict__)
    qemu_reply = loads(str(response))
    return qemu_reply


def guest_info(vmname):
    command = dumps(dict(execute="guest-info", ))
    response = virsh("qemu-agent-command", vmname, command)
    qemu_reply = loads(str(response))
    return qemu_reply


if __name__ == '__main__':
    run(docopt(__doc__))
