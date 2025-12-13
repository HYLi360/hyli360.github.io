---
title: "使用subprocess模块创建附加进程"
tags: ["Python", 标准库]
date: 2025-12-13 16:03:50 +0800
description: "以调用外部程序，或者实现进程串联与交互。"
categories: ["Python", "标准库"]
---

`subprocess` 模块自 Python 3.5 起正式引入，并取代旧有的 `os.system` 与 `os.spawn*`，以及旧有的 `run()`、`check_call` 和 `check_output` API（即使这些 API 目前仍然可用）。该模块的基本功能是建立一个新进程，调用方法类似于在终端里执行一条 command，但标准输出与标准错误输出可被 Python 捕获。这很适用于在 Python 代码中调用外部命令的场景（例如使用 Python 库无法提供的功能）。

这些例子已经在笔者的 Ubuntu + Python 3.14 平台上得到测试，且在 Windows 上进行了验证。

## subprocess.run()

```py
import subprocess

subprocess.run(["echo", "Hello, World!"])                                 # 仅执行，但不捕获 stdout 与 stderr
subprocess.run(["echo", "Hello, World!"], capture_output=True)            # 捕获 stdout 与 stderr
subprocess.run(["echo", "Hello, World!"], capture_output=True, text=True) # 以字符串返回
```

`subprocess.run` 的基本用法如下：

```py
subprocess.run(args, *, stdin=None, input=None, stdout=None, stderr=None,
               capture_output=False, shell=False, cwd=None, timeout=None,
               check=False, encoding=None, errors=None, text=None, env=None,
               universal_newlines=None, **other_popen_kwargs)
```

不过多数人还是喜欢这种：

```py
subprocess.run(["此处", "填写", "一条命令",], capture_output=True, text=True)
```

这里最常用的参数包括：

- `args`，具体要执行的命令，可以是字符串，也可以是一个列表。不过更建议使用列表，可以避免命令注入的风险。
- `stdin`、`stdout` 与 `stderr` 是该子进程的标准输入、标准输出与标准错误输出位置。一般情况下不用管它们；但如果想阻止输出 `stderr`，可以设 `stderr=subprocess.DEVNULL`。
- `capture_output` 是在问是否让 Python 捕获该进程的标准输出与标准错误输出。
- `shell`，即是否通过操作系统的 Shell 执行该命令。默认情况下是 `False`，因为 Windows 和 POSIX 调用的 Shell 是不一样的（Windows 是 `cmd.exe /c`，而 POSIX 是 `sh -c`），使用 `shell` 会引发跨平台问题。
- `cwd` 指该进程的工作目录。
- `timeout`，可设置进程最长维持时间。如果 `timeout` 秒内该进程仍未返回结果，则强制取消该进程。
- `check` 用来检查程序返回码是否为 0。

> ### Python 2 旧 API 与 `subprocess.run` 不同写法的关联
>
> | 旧写法                         | 基于 `subprocess.run()` 的等效写法                           |
> | ------------------------------ | ------------------------------------------------------------ |
> | `subprocess.call(cmd)`         | `subprocess.run(cmd).returncode`                             |
> | `subprocess.check_call(cmd)`   | `subprocess.run(cmd, check=True)`                            |
> | `subprocess.check_output(cmd)` | `subprocess.run(cmd, check=True, stdout=subprocess.PIPE).stdout` |

## CompletedProcess、capture_output 与 text

`process.run()` 会产生一个 `CompletedProcess` 类，包含命令参数与返回码；另外，如果你选择 `capture_output`，你还会得到 `stdout` 与 `stderr`。请注意这三条命令中 `proc` 的微妙变化：

```py
import subprocess

proc = subprocess.run(["echo", "Hello, World!"])
print(proc)

"""
CompletedProcess(args=['echo', 'Hello, World!'], returncode=0)
"""

proc = subprocess.run(["echo", "Hello, World!"], capture_output=True)
print(proc)

"""
stdout 与 stderr 以二进制表示

CompletedProcess(args=['echo', 'Hello, World!'], returncode=0, stdout=b'Hello, World!\n', stderr=b'')
"""

proc = subprocess.run(["echo", "Hello, World!"], capture_output=True, text=True)
print(proc)

"""
stdout 与 stderr 以字符串表示

CompletedProcess(args=['echo', 'Hello, World!'], returncode=0, stdout='Hello, World!\n', stderr='')
"""
```

## 该不该使用“shell=True”？

如果 `shell=True`，`subprocess` 会创建一个 Shell 中间进程，并让它执行这个命令。其原理是将

```py
[args[0], args[1], ...]
```

替换为

```py
['/bin/sh', '-c', args[0], args[1], ...]
```

在 WinCMD 上也是类似，会在前面插入终端的实际路径，再将其他参数的位置向后错开。

如果设置为 `False`，则**采用实际的可执行文件执行命令**（不管这个可执行文件是在 *cwd*，还是在环境变量里）。

但是——有时这些指令甚至直接指向可执行文件，因此不使用 `shell=True` 也没问题。这在 POSIX 是很常见的，因此常在 Linux 编程的程序员总是在这一点上偷懒。

例如，我在 Linux 上使用 `subprocess.run` 执行了 `["ls"]`，无论是否 `shell=True`，结果都是一致的。后来在终端里执行了一下 `which ls` 以查找对应的可执行文件，最后发现 `ls` 实际上就是指向了一个可执行文件 `ls`：

```sh
$ which ls
/usr/bin/ls
```

而在 Windows，问题就随之浮现——你找不到哪里有 `dir.exe`，或者是 `echo.exe`，因为它们是内建指令，并不对应任何可执行文件。因此，要在 Windows 上进行 `echo`，你就不得不使用 `shell=True`。

```
# 如果不使用 shell=True，就会报告 FileNotFoundError：
FileNotFoundError: [WinError 2] 系统找不到指定的程序。

# 如果设置 shell=True，就会恢复正常
"Hello, world!"
CompletedProcess(args=['echo', 'Hello, world!'], returncode=0)
```

但搞笑的是，在 CMD 上运行 `where where`，竟然真的能找到它对应的可执行程序：

```cmd
>where where
C:\Windows\System32\where.exe
```

所以，为了避免这种复杂情况，还是需要遵守这些规则：

1. **能使用 Python API，就不要调用外部程序。**`os`、`pathlib` 等基本库是完全跨平台的，可以完全规避这种复杂问题。
2. **如果你需要调用的就是个可执行文件，那么最好保持 `shell=False`，因为根本不需要。**
3. 除非你确实使用终端的内建指令，或者利用 POSIX 系统的管道特性，且环境受控（无需担心通过你的脚本向终端注入恶意指令的情形），否则也应当保持 `shell=False`。

## 如何安全调用一个外部程序？

要调用一个外部程序，首先要保证它是否存在且可调用。Python 提供了 `shutil.which()`，它是 `which`（POSIX）与 `where`（WinCMD）的 Python 版本，因此同样无需担心跨平台问题。

回到 Ubuntu，尝试使用 `shutil.which()` 找到 `echo` 的可执行文件路径： 

```py
import shutil

print(shutil.which("echo"))

"""
/usr/bin/echo
"""
```

实在不放心，可限定其搜索范围，并检查其 `version`：

```py
import shutil
import subprocess

print(shutil.which("echo", path="/usr/bin:bin"))  # path 的这种写法来自环境变量
print(subprocess.run(["echo", "--version"], capture_output=True, text=True, check=True))

"""
/usr/bin/echo
CompletedProcess(args=['echo', '--version'],returncode=0, stdout='echo (uutils coreutils) 0.2.2\n', stderr='')
"""
```

可以看到，`shutil.which()` 找到了文件路径，且 `version` 命令正确返回结果。

## stdin、stdout 与 stderr

这三个参数可用来定义该命令中标准输入、标准输出与标准错误输出的位置。常见用法如下：

- `subprocess.DEVNULL`，相当于“垃圾桶”，可以将不需要的输出重定向至此处。例如，设置 `stderr=subprocess.DEVNULL` 可抑制不需要的错误输出。
- `subprocess.STDOUT`，主要给 `stderr` 使用，用来将标准错误输出重定向至标准输出。
- `subprocess.PIPE`，充当进程间的管道。在 `subprocess.Popen` 部分会进一步说明。

## 相关错误

`subprocess` 下的所有错误类别均派生自基类 `SubprocessError`。

- `CalledProcessError`：非 0 返回码。当该进程以非 0 返回码结束，且设置了 `check=True`，则抛出此异常。

- `TimeoutExpired`：命令超时。在 `subprocess.run()` 里设置 `timeout` 参数，如果该命令在 `timeout`（秒）内没有完成，就会抛出此异常。

## 更高级的子进程创建方法：subprocess.Popen

> 以下这些案例都基于 POSIX 系统。Windows 上虽然没有这些指令，但仍然支持管道和信号特性。后面会提供同时兼容这两个平台的示范代码。

`subprocess.run()` 有两个令人不适之处：首先它会**阻塞主进程**，而不是作为一个真正分离的进程运行；其次，做各种**管道操作**也不太方便。

因此，更高级的方案是使用 `subprocess.Popen`。事实上，`run()`、`call()`、`check_call()` 和 `check_output` 都是 `Popen` 类的包装器。

```py
class subprocess.Popen(args, bufsize=-1, executable=None, stdin=None, stdout=None,
                       stderr=None, preexec_fn=None, close_fds=True, shell=False,
                       cwd=None, env=None, universal_newlines=None, startupinfo=None,
                       creationflags=0, restore_signals=True, start_new_session=False,
                       pass_fds=(), *, group=None, extra_groups=None, user=None, umask=-1,
                       encoding=None, errors=None, text=None, pipesize=-1, process_group=None)
```

——太长了，不想看！

不过这个类里面，有很多属性其实已经接触过了，例如 `stdin`、`stdout`、`stderr`、`cwd`、`shell`，等等。`run()` 等的工作无非是实例化这个 `Popen` 对象，执行它，最后得到一个 `CompletedProcess` 对象。

不过既然用上了 `Popen`，不玩点最底层的，怎么能算来过这一遭呢。

- 借助 `communicate()` 方法接管其标准输出。

  ```py
  """
  子进程
   ├─ stdout ──▶ Python
   └─ stderr ──▶ 终端
  """
  
  import subprocess
  
  proc = subprocess.Popen(
      ["echo", "Hello, world!"],
      stdout=subprocess.PIPE,
      text=True,
      encoding="UTF-8",
  )
  
  # 实际的输出结果是一个包含 `stdout` 和 `stderr` 的元组
  # 不过该 command 不会产生 `stderr`，因此只看 `stdout` 即可（proc.communicate()[0]）
  print(proc.communicate()[0])
  ```

- 使用 `communicate()` 方法同时接管标准输入与标准输出。

  ```py
  """
  Python 写 stdin
  ↓
  Python 关闭 stdin
  ↓
  cat 收到 EOF
  ↓
  cat 退出
  """
  
  
  import subprocess
  
  proc = subprocess.Popen(
      ["cat", "-"],
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      text=True,
      encoding="UTF-8",
  )
  
  print(proc.communicate("该信息来自标准输入")[0])
  ```

- 继续，同时接管其标准输入、标准输出与标准错误输出。

  ```py
  """
  子进程
   ├─ stdin  ◀── Python
   ├─ stdout ──▶ Python
   └─ stderr ──▶ Python
  """
  
  import subprocess
  
  proc = subprocess.Popen(
      'cat -; echo "该信息来自标准错误输出" 1>&2',
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      shell=True,
      text=True,
      encoding="UTF-8",
  )
  
  print(proc.communicate("该信息来自标准输入\n"))
  # 回想一下，实际的输出结果是一个包含 `stdout` 和 `stderr` 的元组
  # ('该信息来自标准输入\n', '该信息来自标准错误输出\n')
  ```

- 最后，将标准错误输出重定向至标准输出。

  ```py
  """
  子进程
   ├─ stdin  ◀── Python
   └─ stdout ◀── stderr
          │
          └──▶ Python
  """
  
  import subprocess
  
  # 与上一个代码非常相似。看看哪里被改动了？
  proc = subprocess.Popen(
      'cat -; echo "该信息来自标准错误输出" 1>&2',
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      shell=True,
      text=True,
      encoding="UTF-8",
  )
  
  print(proc.communicate("该信息来自标准输入\n")[0])
  ```

> 需特别注意的是，`communicate()` 读取内存是一次性的。如果需要输送大量的数据流，建议用 `iter`（例如 `stdout=PIPE` + `iter(proc.stdout.readline, "")`）。

有了管道，我们可以让多个命令串联起来，或者在两个进程中传递信号。这已经是多进程处理的起点了！

```py
# 这个示范代码同时兼容 Windows 和 POSIX
# 案例1 串联运行两个命令
import subprocess, sys

# 注：sys.executable 表示当前 Python 解释器的完整路径

# p1 将输出一个字符串
p1 = subprocess.Popen(
    [sys.executable, "-c", "print('Hello from p1')"],
    stdout=subprocess.PIPE,
    text=True,
    encoding="UTF-8",
)

# p2 负责将输入的字符串变成大写
p2 = subprocess.Popen(
    [sys.executable, "-c", "import sys; print(sys.stdin.read().upper())"],
    stdin=p1.stdout,
    stdout=subprocess.PIPE,
    text=True,
    encoding="UTF-8",
)

p1.stdout.close()  # 让 p1 在 p2 不再读时能收到 SIGPIPE/等效错误并退出
print(p2.communicate()[0])
```

```py
# 这个示范代码同时兼容 Windows 和 POSIX
# 案例2 在两个进程间交换数据
import subprocess, sys

# 进程 p 的代码，模拟进程 p 与母进程（该脚本执行进程）相互应答的场景
# 如果输入不是 "quit"，则“复读”；
# 否则，发送"bye"，并退出
child_code = r"""
import sys
for line in sys.stdin:
    msg = line.rstrip("\n")
    if msg == "quit":
        print("bye", flush=True)
        break
    print(f"ack:{msg}", flush=True)
"""

p = subprocess.Popen(
    [sys.executable, "-u", "-c", child_code],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True,
    encoding="utf-8",
)

def ask(s: str) -> str:
    p.stdin.write(s + "\n")
    p.stdin.flush()
    return p.stdout.readline().rstrip("\n")

print("[INFO] ", ask("hello"))
print("[INFO] ", ask("ping"))
print("[INFO] ", ask("quit"))

p.stdin.close()
p.wait()

"""
[INFO]  ack:hello
[INFO]  ack:ping
[INFO]  bye
0
"""
```

## 进一步阅读

- [subprocess — Spawning Additional Processes](https://pymotw.com/3/subprocess/index.html)

  国内有中文版，叫《Python 3 标准库》。`subprocess` 库对应该书第 10.1 节。

- [subprocess——子进程管理](https://docs.python.org/zh-cn/3/library/subprocess.html)

  Python 官方的中文文档。

