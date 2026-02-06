---
title: 即时（eager）与延迟（lazy）求值
tags: [Python, Polars]
date: 2026-02-05 23:29 +0800
description: 该懒则懒。
categories: [Python, Polars]
---

Polars 同时支持“即时”与“延迟”计算。“即时”（“及早求值”）模式下，程序会直接执行所在行的代码，这是绝大多数程序（包括 pandas）的默认运行模式；而在“延迟”（“惰性求值”）模式下，程序不会直接执行所在行代码，而是先将它缓存起来，等到真正需要的时候再执行计算，这允许程序在运行时优化其逻辑，从而改善性能。

“惰性求值”本身其实是非常古老的概念，甚至可追溯到 Haskell（默认即惰性求值）、Scheme（`delay`）所在的时期，如今已广泛应用到任何具有函数式编程范式的程序设计语言。仍以 Python 为例，我们非常熟悉的 `range` 其实就是一个不错的起点：

```py
>>> nums = range(2**64)
```

这就很有意思了——我们生成了一个长达 $2^{64}$（约 $10^{19}$）个元素的数列，内存却完全没有任何变化。——我们来尝试取一下里面的值？

```py
>>> nums[10]
10
>>> nums[1000000000]
1000000000
>>> nums[1000000000000000]
1000000000000000
```

它的行为仍然像数组那样，可随意取用范围内的任意数值。——但当你尝试将它转为列表时，就会报告这个错误：

```py
>>> nums = range(2**64)
>>> nums = list(nums)
Traceback (most recent call last):
  File "<python-input-8>", line 1, in <module>
    nums = list(nums)
OverflowError: Python int too large to convert to C ssize_t
```

嗯......好像不是我想看到的结果。我们“稍微”减一些吧——

```py
>>> nums = range(2**32)
>>> nums = list(nums)
Traceback (most recent call last):
  File "<python-input-10>", line 1, in <module>
    nums = list(nums)
MemoryError
```

Python 还是阻止了我们愚蠢的请求。当然我不希望任何人模仿，这几乎必然会导致 OOM。

在 Python 2 中，`range` 确实是“即时”函数，生成的就是一个列表；但在 Python 3，`range` 返回的是一个本身就叫 `range` 的不可变对象，包含起点、终点与步长，内存占用不会超过数百 Bytes。等到你任意“取出”一个元素时，Python 会通过计算而非 indexing 返回结果。强调一下，这是个纯数学计算过程。

> The advantage of the [`range`](https://docs.python.org/3/library/stdtypes.html#range) type over a regular [`list`](https://docs.python.org/3/library/stdtypes.html#list) or [`tuple`](https://docs.python.org/3/library/stdtypes.html#tuple) is that a [`range`](https://docs.python.org/3/library/stdtypes.html#range) object will always take the same (small) amount of memory, no matter the size of the range it represents (as it only stores the `start`, `stop` and `step` values, calculating individual items and subranges as needed).
>
> 相较于常规的 `list` 与 `tuple` 类型，`range` 的优势在于无论它表示的范围如何，它总是占用同样大小（而且非常小）的内存空间（因为它只保存 `start`, `stop` and `step` 三个值，在需要时才会通过计算返回单个元素或子范围）。
>
> [https://docs.python.org/3/library/stdtypes.html#range](https://docs.python.org/3/library/stdtypes.html#range)

----

不过 `range` 的例子并不好迁移到其他地方，因为我们遇到的大部分数据都具有不等的 `step`（步长），甚至不知道起点与终点（`start` 与 `end`），但仍需要利用 `range` 那种惰性求值优势。这时，我们需要使用另一种工具：迭代器（iterator）。

迭代器与上面那个 `range` 不同：

- 你只能正向移动，不能反向移动。迭代器只能从头遍历到尾。

  ```py
  >>> ls = ["I", "LOVE", "Python", "!"]
  >>> it = iter(ls)
  >>> for x in it:
  ...     print(x)
  ...     
  I
  LOVE
  Python
  !
  >>> for x in it:
  ...     print(x)
  ...
  >>> # 可看到再次遍历时没有输出
  ```

- 当然，它也是不可索引/下标的。

  ```py
  >>> ls = ["I", "LOVE", "Python", "!"]
  >>> it = iter(ls)
  >>> it[0]
  Traceback (most recent call last):
    File "<python-input-15>", line 1, in <module>
      it[0]
      ~~^^^
  TypeError: 'list_iterator' object is not subscriptable
  ```

等等？既然都是惰性求值，那我们为何要丢掉 indexing 与下标？还是说它们与惰性求值的理念是冲突的？

Polars 的答案是：我们希望这些函数/方法是指向性明确且可预测的，不会随 DataFrame 的状态而发生改变。

>We believe the semantics of a query should not change by the state of an index or a `reset_index` call ...... Operations like resampling will be done by specialized functions or methods that act like 'verbs' on a table explicitly stating the columns that 'verb' operates on. As such, it is our conviction that not having indices make things simpler, more explicit, more readable and less error-prone.
>
>我们认为，查询的语义不应因索引状态或`reset_index`调用而改变……诸如重采样等操作将由专门的函数或方法完成，这些函数或方法就像作用于表格的“动词”，明确说明该“动词”操作哪些列。因此，我们坚信，不设置索引能使操作更简单、更明确、更易读，并减少出错的可能。
>
>[https://docs.pola.rs/user-guide/migration/pandas/](https://docs.pola.rs/user-guide/migration/pandas/)

简单讲一个例子。我们办公室饮水机里的水喝完了，于是我叫来两个人来打水，其中一个“勤快人”一直记着“一区二栋304”那里可以打水，而另一个“懒人”不这么想，他脑子里只有一个想法：只要这家不是水房，就找下一家，要么就找别人问，绝无“在哪打水”之类的记忆可言。

这里的“一区二栋304”其实就是一个 index。但是世界是不停变化的，“一区二栋304”也会变成“四区三栋201”，甚至改到办公楼楼下，这时再死循着原先的 index，只会是白费功夫。这是一个很关键的问题，你上“一区二栋304”打水，首先就是承认了“一区二栋304”那里就是水房，但 iterator 与 Polars 不这么想，我不相信记忆，只相信“出门之后该做什么”。

当然还有第三种人，这种人更加精明，因为他知道每天早上都会有送水工将水送到楼下，而他只需要跟送水工打好招呼每天早上把水送来，中午再下楼把水搬到楼上。这是惰性计算在 Polars 上的终极形态：LazyFrame。

从这个角度讲，“惰性计算”里的“惰”很难称其为“懒惰”，而是更上一层的精明：我不依赖于记忆，而是根据模式、路径以及路径优化，先选择一条理论最优路线，然后才付诸行动。只不过各自使用的方法不同：`range` 是依赖三个值与一个算式；iterator 只考虑下一个该输出谁；而 Polars 则是从表达式输入先看他需要做什么，等到 `.collect` 口令下来后才开始执行。Polars 的惰性计算还带来了一个“副产品”：由于不需要立刻执行，Polars 有充足的时间进行优化，例如将串行的两个查询并行化。

----

但惰性计算存在两个棘手问题，而且任何一个都非常烫手。

第一个问题来自 [Stack Overflow Q7490768](https://stackoverflow.com/questions/7490768/what-are-haskells-strictness-points)，楼主询问 Haskell 这种“默认即惰性”的语言在什么时候必须打破这个规则。

>我们都知道（或者应该知道），Haskell 默认是惰性的。除非必须求值，否则不会对任何表达式进行求值。那么，什么时候必须求值呢？Haskell 中确实存在一些必须严格求值的地方。我称之为“严格点”（strictness points），尽管这个术语并没有我想象中那么普及。在我看来：
>
>“Haskell 中的规约（或求值）只发生在严格点。”
>
>那么核心问题在于：Haskell 的严格点究竟是什么？我的直觉认为 `main` 函数、`seq`/bang 模式（`!`）、模式匹配以及通过 `main` 执行的任何 IO 操作都是主要的严格点，但我并不完全清楚为什么我会这么认为。

被采纳的回答中提到了 Launchbury 写的一篇论文 *A Natural Semantics for Lazy Evalution*（《惰性求值的自然语义》），以及查看 GHC 生成的 Core 代码来确定哪些被提前（及早）求值。我不懂 Haskell，所以没办法给出太多意见。

第二名的答案说的还不错：

> 一般说来，我们可以这样描述：
>
> 执行 IO 操作时，要对它“需要”的任何表达式求值......
>
> 正在被求值的表达式（嘿，这是个递归定义！）要对它“需要”的表达式求值。
>
> 从你的直观分类来看，`main` 和 IO 操作属于第一类，而 `seq` 和模式匹配属于第二类。但我认为第一类更符合你提出的“严格点”概念，因为这正是我们在 Haskell 中使评估结果成为用户可观察效应的机制。

也就是说，只有时机相当紧迫，你必须进行回应时，这种“惰性”就会消失，从而坍缩为一个可观测的值。`main` 是程序入口，IO 是程序与外界交流的通道，如果它们都要变成“惰性”，那就如同睡死在家的懒虫一样门都不出，更不要提下楼抬水的事。

另外一些情况，例如模式匹配（有点像 Python 的 `match...case...`），单看 `match`（在 Haskell 里似乎是 `case`？完全反过来了啊！）就不行了，你需要每个分支都展开扫一眼，甚至还要通过计算来查看是否该走这个分支。这时想怠慢都不敢怠慢了。

但程序员能不能手动让它发生坍缩，从而进行观察？`seq` 与 bang pattern 就是所谓的“手工严格点”，如同发令枪——或者在我们这个情境下，我打过来的电话——接到了我的电话，你就要立刻赶过来！这是命令！

另一个问题是顺序破坏。如果研究过编译器优化的问题，你就应该知道我要说什么：是的，我们无法保证 Polars 不会在优化时破坏执行顺序，导致无法预测的计算结果。*Rust Atomics and Locks* 专门有一章讲解内存序，很值得使用 Rust（甚至是 C++）进行并发编程的程序员阅读一下，但这里不会讲那么深入，我们还是简单进行说明。

```py
>>> def add_one_and_count(x: int) -> int:
...     global counter # 读取外部状态
...     counter += 1   # 又更改了外部状态
...     print(f"Called {counter} times!") # print 引发了可观测的副作用
...     return x+1
...     
>>> counter = 0
>>> add_one_and_count(5)
Called 1 times!
6
>>> add_one_and_count(5)
Called 2 times!
6
>>> add_one_and_count(5)
Called 3 times!
6
```

可以看到，输入与输出是一致的，但与此同时，`counter` 作为外部世界状态发生了改变并通过 `print` 被我们发现，这便是“副作用”（side-effect）。

惰性查询只对“最终数据结果”负责，而优化后的执行路径（并行、分块、重排、裁剪）不保证与源码书写顺序一致。在 Polars 中，表达式系统默认假设计算是纯的；一旦引入 Python UDF（如 `map_elements`），它就成为优化器无法理解的黑盒，不仅性能会退化到 Python 逐元素循环（这是官方强烈不推荐的一个原因），还会让 UDF 的调用次数/顺序/时机变得不可依赖，从而任何依赖外部状态（计数器、日志、随机数、时间、写文件等）的副作用都可能产生不可预测的可观测差异。

Haskell 使用 IO Monad 隔离副作用，而 Polars 则先用 LazyFrame 隔离它，再用自己的列表达式/声明式语言（而非 Python 的命令式语言）防止副作用的发生。任何表达式都是以列为单位的纯变换，不会引发任何可观测的不一致行为。

惰性带来的查询优化需要以限制程序员表达为代价——但即便如此，Polars 仍然尽全力让程序员能够轻松表达自我。例如，在 pandas，完全不会有人阻止你这样做：

```py
for i in range(len(df)):
    if df.iloc[i]["x"] > 0:                     # 随意 indexing！
        df.iloc[i]["y"] = df.iloc[i]["y"] * 2   # 随意变异！
        print(f"Modified row {i}")              # 随意副作用！
        if some_external_api_check(df.iloc[i]): # 随意 IO！
            break                               # 随意控制流！
```

在 Polars，你无法做到这些。但在框架之下也并非无路可走：

```py
# 表达式 DSL
# 这是基于表达式实现的 if-then-else 逻辑
pl.when(pl.col("x") > 0).then(pl.col("y") * 2) .otherwise(pl.col("z"))

# 窗口函数
# 它可以替代 pandas 的 groupby 与 transform
pl.col("y").sum().over("group")

# 显式回退
# 使用“map_elements”即接受性能惩罚
def f(x):
    print("seen", x)   # 副作用
    return x * 2
df.with_columns(pl.col("x").map_elements(f))

# 完全回退到 eager 世界
df.collect().to_pandas().apply(...)
```

“暂时的后退换来继续前进的潜力”。Rust 语言本身也是如此：使用更加高深难懂的“所有权模型”“借用与可变借用”“生命周期”等概念，抛弃了 GC，革除了“野指针”，换来了数理逻辑上的“内存安全”。说不上这么做到底有没有意义，反正 Rust 和 Polars 把这些问题都啃下来了，还活的不错。

不过 pandas 最近也开始发力——今年 1 月，[pandas 3.0](https://pandas.pydata.org/docs/whatsnew/v3.0.0.html) 已经带着 CoW（写时复制）与 PyArrow 后端再次杀出重围，甚至将 Polars 的部分语法给学了去：

```py
>>> df.assign(c = pd.col('a') + pd.col('b')) 
   a  b  c
0  1  4  5
1  1  5  6
2  2  6  8
```

Polars 的强大竟反过来帮助了 pandas 的进步。没想到啊，大家都能有光明的未来。

