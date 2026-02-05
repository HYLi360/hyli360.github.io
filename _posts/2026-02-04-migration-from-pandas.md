---
title: "从Pandas转到Polars"
tags: [Python, Polars]
date: 2026-02-04 22:48 +0800
description: "你必须要知道的一些事情。"
categories: [Python, Polars]
---

> 该文章翻译自 [https://docs.pola.rs/user-guide/migration/pandas/](https://docs.pola.rs/user-guide/migration/pandas/)。
{: .prompt-info }

以下是任何有 Pandas 编程经验的程序员尝试使用 Polars 时必须注意的几个要点，内容包括两个方面：两个库构建理念上的差异，以及相较于 Pandas，使用 Polars 编程时需要留意的不同之处。

## 概念（Concepts）

### Polars 没有索引（index）与多重索引的概念。

Pandas 会给每一行提供一个标签（即 `.index`）作为索引。Polars 不会这样做，而是通过每行数据在表中的整数位置进行定位。

Polars 旨在提供可预测的结果与可读的查询语句，因此我们认为索引无助于我们实现这个目的。我们相信，查询语句不应随索引状态、或者调用 `reset_index` 而随之改变。

在 Polars，一个 `DataFrame` 始终是具有异构类型的二维表格。数据类型可以嵌套，但表格本身不会。“重采样”（resampling）之类的操作会通过专门的函数/方法来完成，这些函数/方法就如同作用于表格的“动词”，明确指向该“动词”要操作的列。因此我们坚信，不使用索引能够让操作更简洁、更明确、更易读且更难出错。

需注意，数据库中常见的“索引”数据结构，在 Polars 中将作为优化技术使用。

### 与 Pandas 使用 NumPy 数组不同，Polars 遵循 Apache Arrow 内存格式在内存中表示数据。

Polars 根据 Apache Arrow 内存规范在内存中表示数据，而 Pandas 默认使用 NumPy 数组。Apache Arrow 是一种新兴的内存列式分析标准，能够缩短数据加载时间、减少内存使用并提升计算效率。

如有需要，用户可通过 `to_numpy` 方法将数据转为 NumPy 数组。

### 与 Pandas 相比，Polars 支持更多的多线程操作。

Polars 充分利用 Rust 程序设计语言对并发编程的支持，实现了众多操作的并行执行。虽然 Pandas 的部分操作支持多线程，但其核心库仍以单线程运行为主，必须借助 Dask 等额外库才能实现并行化。在并行化 Pandas 代码的所有开源解决方案中，Polars 展现出最快的运行速度。

### Polars 支持多种计算引擎。

Polars 原生支持两种引擎：针对内存处理优化的引擎，以及专为大规模数据处理优化的流式引擎。Polars 还原生集成支持 cuDF（GPU 加速）的计算引擎。这些引擎都将得益于 Polars 的查询优化器，且 Polars 可在不同引擎之间确保语义一致性。相比之下，Pandas 的实现可以在 NumPy 和 PyArrow 之间进行调度，但由于 Pandas 的严格性保证较弱，不同后端之间的数据类型输出及语义可能存在差异，这会导致难以察觉的错误。

### Polars 支持“延迟求值”（lazily evaluation）与查询优化。

“即时求值”（eager evaluation）指代码运行后会立即执行计算。“延迟求值”则是运行到代码所在行时，先保存其底层逻辑至查询计划中，而不是直接执行计算。

Polars 同时支持“即时求值”与“延迟求值”，而 Pandas 只支持“即时求值”。“延迟求值”之所以强大，在于 Polars 可在分析查询计划时自动执行查询优化，以寻找加速查询或降低内存占用的方法。

Dask 在生成查询计划时同样支持“延迟求值”。

### Polars 很严格。

Polars 对数据类型要求严格。其数据类型解析依赖操作图，而 Pandas 则采用宽松的类型转换，例如新出现的缺失数据可能导致整数类型的列被转为浮点类型。这种严格性可减少错误，并让行为更可预测。

### Polars 拥有更灵活的 API。

Polars 基于表达式构建，几乎所有操作都支持表达式输入。这意味着一旦理解了 Polars 表达式的工作原理，您就能轻松地举一反三。Pandas 则没有表达式系统，往往需 Python 的 `lambda` 表达式满足复杂需求。Polars 将“依赖 Python lambda 函数”视作 API 表达能力的不足，并尽可能为您提供原生支持。

## 关键语法差异概览

从 Pandas 来的程序员在使用 Polars 时，将逐渐地意识到：

```
polars != pandas
```

如果你写出了像 Pandas 的 Polars 代码，它或许能运行，但不会达到 Polars 能达到的速度。

让我们用几个典型的 Pandas 代码作为示范，看看如何用 Polars 重写它们。

### 选择数据

因为没有了索引，Polars 没有 Pandas 的 `.loc`/`.iloc` 方法，也不会有类似 `SettingWithCopyWarning` 的警告。

不过，在 Polars 里，选择数据的最佳方式是使用表达式 API。例如，你在 Pandas 会用它来选择某一列数据：

```py 
df["a"]
```

或者

```py
df.loc[:,["a"]]
```

但在 Polars，你有 `.select` 方法：

```py
df.select("a")
```

如果要根据某一列的值选择相应的行，可以用 `.filter` 方法：

```py
df.filter(pl.col("a") < 10)
```

就像下面“表达式”小节里的说明那样，Polars 可并行执行像 `.select`、`.filter` 这样的操作，并可根据完整的数据选择条件进行查询优化。

### 巧用“延迟求值”

在Polars中，采用“延迟求值”进行工作非常简单，也应作为默认设置，因为它能让 Polars 实现查询优化。

我们可以通过使用隐式延迟函数（例如 `scan_csv`），或显式使用 `lazy` 方法来运行延迟模式。

以下这个简单的示例，演示了我们如何从磁盘读取一个 CSV 文件并执行分组操作。该 CSV 文件包含多个列，但我们只需对其中一个 ID 列（`id1`）进行分组，然后按值列（`v1`）求和。在 Pandas 上，一般需要这么做：

```py
df = pd.read_csv(csv_file, usecols=["id1","v1"])
grouped_df = df.loc[:,["id1","v1"]].groupby("id1").sum()
```

但在 Polars 上，你可以将 Pandas 上的 `read_csv`（“即时求值”）换成 `scan_csv`（“延迟求值”），从而享受到延迟求值带来的查询优化：

```py
df = pl.scan_csv(csv_file)
grouped_df = df.group_by("id1").agg(pl.col("v1").sum()).collect()
```

Polars 通过只识别 `id1` 与 `v1` 两列来优化此查询，因此只会从 CSV 文件读取 `id1` 与 `v1` 两列。通过调用 `.collect()` 方法，我们指示 Polars 立即执行该查询。

想以“即时求值”方式运行该查询，只需将上述 Polars 代码中的 `scan_csv` 替换为 `read_csv`。

您可在 [延迟 API](https://docs.pola.rs/user-guide/lazy/using/) 章节中了解更多关于延迟求值的细节。

### 尽情“表达”你自己

典型的 Pandas 脚本包含一系列按顺序执行的数据转换操作。但在 Polars，这些转换可通过表达式系统并行化执行。

#### 列赋值

假设有一个 DataFrame `df`，其中有一列叫 `value`。我们希望再加两列，一列叫 `tenXValue`，表示将 `value` 这一列乘以 10；另一列叫 `hundredXValue`，表示将 `value` 乘以 100。

在 Pandas，你需要这样写：

```py
df.assign(
    tenXValue=lambda df_: df_.value * 10,
    hundredXValue=lambda df_: df_.value * 100
)
```

或者更直接的：

```py
df["tenXValue"] = df["value"] * 10
df["hundredXValue"] = df["value"] * 100
```

但本质上是一样的：Pandas 会将它们当作两次赋值来执行。

而在 Polars，我们使用 `.with_columns` 进行赋值：

```py
df.with_columns(
    tenXValue=pl.col("value") * 10,
    hundredXValue=pl.col("value") * 100,
)
```

看上去差不多，但它们会在 Polars 上同时执行。

#### 基于谓词的列赋值

在该情景下，我们有一个包含 `a` `b` `c` 3 列的 DataFrame `df`。我们希望根据 `a` 列的值，基于条件重新进行赋值：当 `c` 列的值为 2 时，用 `b` 的值覆盖 `a` 的值。

在 Pandas 上是这样的：

```py
df.assign(a=lambda df_: df_["a"].mask(df_["c"] == 2, df_["b"]))
```

而在 Polars 上，是这样的：

```py
df.with_columns(
    pl.when(pl.col("c") == 2)
    .then(pl.col("b"))
    .otherwise(pl.col("a")).alias("a")
)
```

Polars 可并行处理 `if->then->otherwise` 上的每一个分支。当分支的计算成本增加时，这一点尤为宝贵。

#### 筛选

我们需要根据特定条件对包含住房数据的 DataFrame `df` 进行筛选。

在 Pandas 中，可以通过向 `query` 方法传递布尔表达式来筛选 DataFrame：

```py
df.query("m2_living > 2500 and price < 300000")
```

或者直接通过评估掩码条件实现：

```py
df[(df["m2_living"] > 2500) & (df["price"] < 300000)]
```

而在 Polars 中，需要调用 `filter` 方法：

```py
df.filter(
	(pl.col("m2_living") > 2500) & (pl.col("price") < 300000)
)
```

Polars 的查询优化器能够自动检测单独编写的多个筛选条件，并在优化执行计划时将其合并为单个筛选操作。

### Pandas 的“transform”

Pandas 的文档里演示了一组名叫 `transform` 的操作。在该案例中，我们有一个 DataFrame `df`，我们想加一个新列来显示各组行数。

在 Pandas 上，我们是这样做的：

```py
df = pd.DataFrame({
    "c": [1, 1, 1, 2, 2, 2, 2],
    "type": ["m", "n", "o", "m", "m", "n", "n"],
})

df["size"] = df.groupby("c")["type"].transform(len)
```

这里 Pandas 先对 `c` 列执行了 `groupby`，然后提取 `type` 列，计算组的长度，再将结果重新接回 `df`，从而得到

```
   c type size
0  1    m    3
1  1    n    3
2  1    o    3
3  2    m    4
4  2    m    4
5  2    n    4
6  2    n    4
```

在 Polars，我们可以用 `windows` 函数实现同样的操作：

```py
df.with_columns(
    pl.col("type").count().over("c").alias("size")
)
```

```
shape: (7, 3)
┌─────┬──────┬──────┐
│ c   ┆ type ┆ size │
│ --- ┆ ---  ┆ ---  │
│ i64 ┆ str  ┆ u32  │
╞═════╪══════╪══════╡
│ 1   ┆ m    ┆ 3    │
│ 1   ┆ n    ┆ 3    │
│ 1   ┆ o    ┆ 3    │
│ 2   ┆ m    ┆ 4    │
│ 2   ┆ m    ┆ 4    │
│ 2   ┆ n    ┆ 4    │
│ 2   ┆ n    ┆ 4    │
└─────┴──────┴──────┘
```

由于整个操作可存储于单个表达式中，我们能组合多个窗口函数，甚至还能合并不同分组！

Polars 会缓存应用于相同分组的窗口表达式，因此将它们存储在单个 `with_columns` 中既便捷又高效。下例展示了对 `c` 进行两次分组统计的情况：

```py
df.with_columns(
    pl.col("c").count().over("c").alias("size"),
    pl.col("c").sum().over("type").alias("sum"),
    pl.col("type").reverse().over("c").alias("reverse_type")
)
```

```
shape: (7, 5)
┌─────┬──────┬──────┬─────┬──────────────┐
│ c   ┆ type ┆ size ┆ sum ┆ reverse_type │
│ --- ┆ ---  ┆ ---  ┆ --- ┆ ---          │
│ i64 ┆ str  ┆ u32  ┆ i64 ┆ str          │
╞═════╪══════╪══════╪═════╪══════════════╡
│ 1   ┆ m    ┆ 3    ┆ 5   ┆ o            │
│ 1   ┆ n    ┆ 3    ┆ 5   ┆ n            │
│ 1   ┆ o    ┆ 3    ┆ 1   ┆ m            │
│ 2   ┆ m    ┆ 4    ┆ 5   ┆ n            │
│ 2   ┆ m    ┆ 4    ┆ 5   ┆ n            │
│ 2   ┆ n    ┆ 4    ┆ 5   ┆ m            │
│ 2   ┆ n    ┆ 4    ┆ 5   ┆ m            │
└─────┴──────┴──────┴─────┴──────────────┘
```

### 缺失数据

pandas 根据列的数据类型使用 `NaN` 和/或 `None` 值来表示缺失值。此外，Pandas 的行为会根据是否使用默认数据类型或可选的可空数组而有所不同。而在 Polars 中，所有数据类型的缺失数据都对应一个 `null` 值。

对于浮点数列，Polars 允许使用 `NaN` 值。这些 `NaN` 值不被视为缺失数据，而是一种特殊的浮点数值。

在 Pandas 中，带有缺失值的整数列会被转换为浮点数列，缺失值用 `NaN` 表示（除非使用可选的可空整数数据类型）。而在 Polars 中，整数列中的任何缺失值都只是 `null` 值，并且该列仍然保持为整数列。

更多详细信息，请参阅 [缺失数据](https://docs.pola.rs/user-guide/expressions/missing-data/) 部分。

### 管道滥用

在 Pandas 中，一个常见的用法是利用管道（`pipe`）对 DataFrame 应用某些函数。将这种编码风格照搬到 Polars 中是不符合其惯用法的，并且会导致查询计划不够优化。

下面的代码片段展示了 Pandas 中的一个常见模式。

```py
def add_foo(df: pd.DataFrame) -> pd.DataFrame:
    df["foo"] = ...
    return df

def add_bar(df: pd.DataFrame) -> pd.DataFrame:
    df["bar"] = ...
    return df


def add_ham(df: pd.DataFrame) -> pd.DataFrame:
    df["ham"] = ...
    return df

(df
 .pipe(add_foo)
 .pipe(add_bar)
 .pipe(add_ham)
)
```

如果在 Polars 中采用这种做法，我们将创建三个独立的 `with_columns` 上下文，这会强制 Polars 按顺序执行这三个管道操作，无法利用任何并行处理能力。

在 Polars 中获得类似抽象的方法是创建生成表达式的函数。下面的代码片段创建了三个表达式，它们运行在同一个上下文中，因此可以并行执行。

```py
def get_foo(input_column: str) -> pl.Expr:
    return pl.col(input_column).some_computation().alias("foo")

def get_bar(input_column: str) -> pl.Expr:
    return pl.col(input_column).some_computation().alias("bar")

def get_ham(input_column: str) -> pl.Expr:
    return pl.col(input_column).some_computation().alias("ham")

# 此单一上下文将并行运行所有3个表达式
df.with_columns(
    get_ham("col_a"),
    get_bar("col_b"),
    get_foo("col_c"),
)
```

若要在生成表达式的函数中使用模式（schema），可采用单个 `pipe`：

```py
from collections import OrderedDict

def get_foo(input_column: str, schema: OrderedDict) -> pl.Expr:
    if "some_col" in schema:
        # 分支 a
        ...
    else:
        # 分支 b
        ...

def get_bar(input_column: str, schema: OrderedDict) -> pl.Expr:
    if "some_col" in schema:
        # 分支 a
        ...
    else:
        # 分支 b
        ...

def get_ham(input_column: str) -> pl.Expr:
    return pl.col(input_column).some_computation().alias("ham")

# 使用管道（仅一次）来获取 LazyFrame 的结构信息。
lf.pipe(lambda lf: lf.with_columns(
    get_ham("col_a"),
    get_bar("col_b", lf.schema),
    get_foo("col_c", lf.schema),
))
```

编写返回表达式的函数有另外一个好处：这些函数具有可组合性，表达式既可串联又可部分应用，从而在设计上提供了更大的灵活性。

