---
title: "Multiprocessing（一）：多进程、进程池、按序运行与结果收集"
tags: [Python,multiprocessing,科学计算]
date: 2025-12-22 10:16:44 +0800
description: 虽然 Python 作为一个动态且解释型的语言，性能实在不敢恭维，而且还有 GIL 的束缚，但多进程的实现却比想象中还要简单。
categories: [Python]
---

## 多进程基础

使用 `multiprocessing.Process` 类，实例化并启动一个新进程：

```py
from multiprocessing import Process

def f(name):
    print(f"hello, {name}")

# 程序入口。我们会在后面说明这为何有必要
if __name__ == "__main__":
    p = Process(target=f, args=("bob", ))
    p.start()
    p.join()
```

`Process` 这个类具体来说：

```py
class multiprocessing.Process(group=None, target=None, name=None, args=(), kwargs={}, *, daemon=None)
```

它和 `threading.Thread` 非常相似：

```py
class threading.Thread(group=None, target=None, name=None, args=(), kwargs={}, *, daemon=None, context=None)
```

不过不同的是，在 `Process` 上：

- `group` 参数是无效的（必须是 `None`）。
- 没有 `content` 参数（因为进程之间无法共享上下文）。
- 额外实现了“终结”（`terminate()`）、“杀死”（`kill()`）和“中断”（`interrupt()`）的方法。

这并非来自继承，而是源自“多线程到多进程”的思想转变——因为多线程的实现先于多进程。`Process` 类的设计是为了在接口上与 `Thread` 相兼容，从而方便地从 `threading` 模块迁移到 `multithreading`。另外，虽然它们都具有 `start`、`join` 和 `run` 方法，但底层实现截然不同。

回到 `Process`。这里我们看到 `p` 还有两个方法：`start()` 和 `join()`。`start()` 用来启动这个进程，而 `join()` 可以产生“阻塞”：直到这个进程结束，才能继续执行后面的代码。

但别忘了——还有个 `run()` 方法呢！听上去似乎也能用来启动这个进程。不过有意思的是，在主程序里，你不可能连续对同一个 `Process` 做两次 `start`，但两次 `run()` 则是被允许的。

```py
Traceback (most recent call last):
  File ".../main.py", line 10, in <module>
    p.start()
    ~~~~~~~^^
  File "/home/linuxbrew/.linuxbrew/opt/python@3.13/lib/python3.13/multiprocessing/process.py", line 115, in start
    assert self._popen is None, 'cannot start a process twice'
           ^^^^^^^^^^^^^^^^^^^
AssertionError: cannot start a process twice
```

查看 `process.py` 源码后发现：

```py
 class BaseProcess(object):
    ......
    def run(self):
        '''
        Method to be run in sub-process; can be overridden in sub-class
        '''
        if self._target:
            self._target(*self._args, **self._kwargs)

    def start(self):
        '''
        Start child process
        '''
        self._check_closed()
        assert self._popen is None, 'cannot start a process twice'
        assert self._parent_pid == os.getpid(), \
               'can only start a process object created by current process'
        assert not _current_process._config.get('daemon'), \
               'daemonic processes are not allowed to have children'
        _cleanup()
        self._popen = self._Popen(self)
        self._sentinel = self._popen.sentinel
        # Avoid a refcycle if the target function holds an indirect
        # reference to the process object (see bpo-30775)
        del self._target, self._args, self._kwargs
        _children.add(self)
```

不需要过多理解其逻辑，简单来说，`start()` 执行前要进行一系列检查，包括是否执行过该函数（包括该函数携带的参数），然后才在子进程那里执行 `run()`（在 `_bootstrap()` 那儿）；而 `run()` 只是在主进程（父进程）中（再次）执行那个函数而已。**直接使用 `run()`** 有可能导致重复执行，且**会破坏并行关系**。

事实上，`Process` 类的 `run()` 方法是用来被覆写的，指示这个进程接下来做什么（这样也省去写 `target` 的需求了）：

```py
from multiprocessing import Process

class Hello(Process):
    def run(self) -> None:
        print(f"hello, bob!")

if __name__ == "__main__":
    p = Hello()
    p.start()
```

但我们不会这么做，因为这相当 stupid，也很不灵活，甚至不如设 `target`。

---

我反复讲过，Python 是一个具有可移植性的语言——即便目标如此，由于 Windows 与 POSIX 不同的系统 API，**同一个 Python 类方法会有完全不同的实现手段，而这种不同会引发各种意料外的副作用**。

`multiprocessing` 支持这三种启动进程的方式：

- `spawn`，也就是让子进程通过重复主进程的行为来实现初始化。这种方法是最为安全的，因为 Windows 和 POSIX 都支持这个方法，但会增加启动子进程所需的时间开销。

  此外，它还有一个潜在的隐患：**子进程要完全重复主进程的行为**，岂不是要将主进程启动子进程的行为一并学去？这就会引发一场无止尽的递归：爷爷启动爸爸，爸爸启动儿子，儿子又启动他的儿子......

  因此启动子进程的方法必须且只能让主进程完成，这就是“程序入口点”存在的意义。

  ```py
  from multiprocessing import Process
  
  # 主进程，子进程都会执行它
  def f(name):
      print(f"hello, {name}")
  
  # 这部分只有主进程会运行它
  if __name__ == "__main__":
      p = Process(target=f, args=("bob", ))
      p.start()
      p.join()
  ```

  其中 `__name__` 是任何一个进程都具有的属性。对于主进程，它的 `__name__` 就是 `__main__`；由主进程分支出的其他子进程，其 `__name__` 就不是 `__main__`：

  ```py
  import multiprocessing as mp
  from multiprocessing import Process
  
  # 主进程，子进程都会执行它
  def f(name):
      print(f"hello, {name}")
  print(__name__)
  
  # 这部分只有主进程会运行它
  if __name__ == "__main__":
      mp.set_start_method("spawn")
      p = Process(target=f, args=("bob", ),)
      p.start()
      p.join()
  
  # 输出
  # __main__    -> 来自主进程
  # __mp_main__ -> 来自子进程
  # hello, bob  -> 也来自子进程
  ```

  由于 Windows 和 macOS 上，子进程的启动方法默认为 `spawn`，这种保护是至关重要的。

- `fork`。这是 POSIX 独占的其中一种启动方法，原理是调用 `os.fork()`，它会复制出主进程的副本作为子进程（POSIX 经典的写入时复制，即 CoW），并同时运行它们。最后，子进程永远返回 `0`，主进程返回子进程的 ID。

  由于子进程直接从主进程的资源那里拷贝过来，这个过程可以相当快速地完成；麻烦的是，CoW **只会拷贝内存，不会拷贝线程**。例如，主进程有其中一个线程正在修改一个变量，这时子进程把主进程拷贝了过来，但没有拷贝修改变量的线程本身，因此那个变量“Locked”的状态仍然被保留。此时对于那个子进程，这个变量永远无法被改动了，因为他需要等待一个根本不存在的线程结束。这相当地“线程不安全”。

  谢天谢地，该方法自 3.14 开始[不再是默认的启动方法了](https://docs.python.org/zh-cn/3.14/library/multiprocessing.html#contexts-and-start-methods)。

- `forkserver`，这是应对 `fork` 方法线程不安全而提出的解决方案。原理是建立一个长期驻留的服务器进程，每次请求新的子进程时，主进程会与服务器进程连接，并请求其 `fork` 出子进程。服务器进程是完全单线程且内存干净的，且所有子进程完全来自服务器进程，也就是说，这些子进程的内存也是完全干净的。比 `spawn` 快，比 `fork` 安全，但同样仅限于 POSIX。

----

最后，则是**序列化与反序列化的问题**。序列化与反序列化是两种保管数据对象的方式，序列化（*Serialization*）让数据对象转变为字节流以便跨进程传输[^1]，而反序列化让数据对象更方便处理。进程之间要传递数据对象（无论是从主进程到子进程，还是进程之间相互交换数据），都必须经过显式的序列化与反序列化过程，这是由 `pickle` 模块实现的。

麻烦的是，有一些 Python 对象就是不支持序列化，因此有时没办法实现多进程，例如**匿名函数（`lambda`）、线程与进程对象本身、套接字，以及文件句柄（`with open() as f` 里的 `f`）**。

这个序列化过程可以绕过吗？可以，但必须是通过 `fork`。因为 `fork` 能够把内存复制出来，假装你们共享同一块内存状态，而无需传递过程。

不过 `fork` 方法基本被锁死，而 Windows 和 MacOS 更是依赖 `spawn`。这更要提醒我们自己，一定要避开序列化引发的陷阱。

## 进程池

`multiprocessing` 的目的还是在于实现多进程的并行运行。这里需要重点强调**并行**这个概念，它与**并发**有些许不同——“并行”意味着程序的多个部分在同一时刻能够共存，而“并发”只表示能够同时开始，它们可能会共存，也可能按时间次第出现。

假设我们有这样一个工作负载 `worker()`，让它以 5 个进程并行运行：

```py
from multiprocessing import Process
from time import sleep

def worker(name):
    # 模拟工作负载
    sleep(1)
    print(f"hello, {name}")

if __name__ == "__main__":
    for i in range(4):
        p = Process(target=worker, args=("bob", ))
        p.start()

"""
hello, bob
hello, bob
hello, bob
hello, bob
"""
```

如何确定我们开了多个子进程？有一个小方法：无论是在 Windows 还是 POSIX，任何一个进程都分配有一个专属 ID，也就是 PID；`Process` 对象的 `pid` 属性[^2]就代表这个 PID。

需要注意： `Process` 对象只有 `start()` 以后，`pid` 属性才能被赋值，否则一定为 `None`。

```py
from multiprocessing import Process
from time import sleep

def worker(name):
    sleep(1)
    print(f"hello, {name}")

if __name__ == "__main__":
    for i in range(4):
        p = Process(target=worker, args=("bob", ))
        p.start()
        print(p.pid)
        
"""
你不太可能重现出同样的数字，但它们总是连续且递增的
63147
63148
63149
63150
hello, bob
hello, bob
hello, bob
hello, bob
"""
```

如果是针对不同的工作负载（例如更换函数的参数），你可能会这样去写：

```py
from multiprocessing import Process
from time import sleep

def worker(name):
    sleep(1)
    print(f"hello, {name}")

if __name__ == "__main__":
    for name in ["Alice", "Bob", "Carol", "Dave"]:
        p = Process(target=worker, args=(name, ))
        p.start()
```

也没错！不过更加聪明的方法是，使用 `multiprocessing.Pool`，也就是“进程池”。它能够容纳一定数量的进程，还能实现上面这种“批量对一系列的值执行某个函数”的效果。

```py
from multiprocessing import Pool
from time import sleep

def worker(name):
    sleep(1)
    print(f"hello, {name}")

if __name__ == "__main__":
    namelist = ["Alice", "Bob", "Carol", "Dave"]
    with Pool(processes=4) as pool:
        pool.map(worker, namelist)
```

稍稍令人不快的问题是，我们没办法保证输出的顺序与 `namelist` 一致。例如，这是其中一种可能的输出：

```
hello, Bob
hello, Dave
hello, Alice
hello, Carol
```

这是因为，四个子进程结束的顺序并不总是一致。因此我们要额外更改一下逻辑，以返回值的方法重构函数：

```py
from multiprocessing import Pool
from time import sleep

def worker(name):
    sleep(1)
    return f"hello, {name}"

if __name__ == "__main__":
    namelist = ["Alice", "Bob", "Carol", "Dave"]
    with Pool(processes=4) as pool:
        result = pool.map(worker, namelist)
    
    for i in result:
        print(i)
```

虽然四个子进程可能不会按顺序结束，但返回值仍会保持输入的顺序。这也要求我们，**要确保多进程下输入与输出的顺序一致性，最好是将带有返回值的函数作为子任务。**

稍微提一个问题：猜猜看，如果拉进来了第五个人（`Eve`），会发生什么有趣的事情？

试试执行这个代码：

```py
from multiprocessing import Pool
from time import sleep

def worker(name):
    sleep(1)
    print(f"hello, {name}")

if __name__ == "__main__":
    namelist = ["Alice", "Bob", "Carol", "Dave", "Eve"]
    with Pool(processes=4) as pool:
        pool.map(worker, namelist)
```

你会发现，前 4 个人的“hello”会先出现，最后才会出现 `Eve` 的“hello”。这是因为进程池只有 4 个进程的容量，第五个进程要进来，就必须等待进程池里有任意一个进程先完成任务。如果使用“收集返回值”的方法重构函数，你会发现你需要等待 2 秒才能运行完成。

## 实际应用

我们来利用进程池的思想，做一些有趣的事情吧。例如——寻找质数。

**质数是质因数只有 1 和它本身（共两个）的一种数。**对于任何一个数，如果该函数

```py
from math import sqrt

def is_prime(num: int):
    if num % 2 == 0:
        return False
    for i in range(3, int(sqrt(num))):
        if num % i == 0:
            return False
    return True
```

能够返回 `True`，那么它就是一个质数。这是一个相当拙劣的质数搜索法（试除法），不过在这个例子里，我们需要模拟一个很重且容易并行的任务载荷，因此这个例子还算比较合适。

我的笔记本使用的是 i7-13700HX 处理器，具有 16 个核心，24 个线程。因此，我们尝试从 1 进程开始，逐渐增加进程池容量，看看所用时间会如何变化。

```py
from math import sqrt
from multiprocessing import Pool
from timeit import timeit

def is_prime(num: int):
    if num % 2 == 0:
        return False
    for i in range(3, int(sqrt(num))):
        if num % i == 0:
            return False
    return True


def main(i):
    int_sequence_length = 5_000_000
    int_sequence = list(range(1, int_sequence_length+1))
    with Pool(processes=i) as pool:
        pool.map(is_prime, int_sequence)


if __name__ == "__main__":
    for i in range(1, 25):
        def run():
            main(i)
        print(timeit(run, number=1))
```

我们使用 `timeit` 来测量运行时间。需要注意，`timeit` 测出的总运行时间总是比实际更长一些；但在同时使用 `timeit` 的情况下，这些数据仍然是有可比性的。

![plot](/home/hyli360/文档/python_project/PLAYGROUND/plot.png)

可以看到，虽然运行时间随进程数增加而逐渐减少，但变化并非线性。事实上，当进程数比物理核心数还要多时，进程数量增加带来的增益并不显著，这是因为即使是超线程也无法让物理核心增加，本质仍然是同一个物理核心，不同的时间片。

为排除大小核架构可能引发的变化不平衡性，我们又在 EPYC 9654 上进行测试，从 1 进程逐渐增加到 192 进程。另外，数列长度从 5,000,000 增加到 100,000,000。

![plot1](/home/hyli360/文档/python_project/PLAYGROUND/plot1.png)

第一张图有些无聊，也不太容易看出什么；但到了第二张图，我们原本假设总运行时间乘以进程数，应当能够还原回接近单进程运行所需的时间，可结果这个曲线是稳步上升的！是的，甚至没有显著的平台期，就是在逐渐上升！

![plot3](/home/hyli360/文档/python_project/PLAYGROUND/plot3.png)

我们可以将总运行时间与进程数的积当作总 CPU 时间，此时我们看到，进程全开的情况下，CPU 时间反而比单进程长 1 倍都不止。原因有很多，不止是单核与全核状态下不同的时钟频率（单核 3.8GHz vs. 全核 2.4GHz），还有进程分叉并启动，以及数据对象序列化与反序列化造成的开销，更不用说大量内存读写还会造成 I/O 瓶颈。如同杠杆省力不省功，进程增加看似加快运行，其实反而会延长总 CPU 时间。对于按 CPU 时间付费的 HPC 平台，使用多进程计算时不得不高度警惕这个问题——进程确实不是越多越好。

虽然多进程有此严重弊病，但并非无法缓解。我们会在下一章介绍如何解决这个问题——核心的思路是，将进程的粒度增大，允许进程之间共享内存，并适当压缩进程数量。尽管这些方法比多进程并行化本身更加棘手，但为了压低 CPU 时间，这些仍然是相当值得的。∎



---

[^1]: 在多线程环境下不需要这么做，因为他们能够共享内存。
[^2]: `Process` 对象的 `pid` 和 `ident` 属性都代表 PID，只是名字有所不同。`ident` 属性的存在也是为了与 `Thread` 对象兼容。[Stack Overflow Q45860547](https://stackoverflow.com/questions/45860547)
