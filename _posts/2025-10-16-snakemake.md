---
title: Snakemake用法介绍
tags: snakemake
date: 2025-10-16 19:28:11 +0800
description: 复现是任何科学站得住脚的根本前提。
categories: 工具
---

**Snakemake** 是基于 Python 开发的工作流管理框架，旨在通过一个人类可读的文件实现可重复的数据分析流程。其语法兼容 Python 解释器，但语法风格与设计理念很像 GNU Make。

虽然它主要被用于生物信息学分析，但 Snakemake 的用途并不限于该领域；任何可通过 pipeline 实现自动化的数据分析流程，皆可使用 Snakemake。官方声称其**下载量超 120 万次，每周新增至少 14 篇文章引用**（含新旧两版论文）。

## 安装

`conda install -c conda-forge snakemake -y`

## 最简案例

```
# 文件夹根目录下的文件 ./Snakefile
rule all:
    input:
        "result/path/here",

rule count_words:
    input:
        "input/path/here",
    output:
        "output/path/here",
    shell:
        "command {input} {output}",

```

其中

- `rule` 是规定 workflow 步骤的关键字。`rule all` 表示该 workflow 的目标。
- 其他则表示需要执行的各种流程。

Snakemake 可通过 DAG（有向无环图）**自动分析执行顺序**，因此子步骤的顺序并不重要，仅需确保依赖关系正确。

## 通配符与批处理

通配符（此处即 **wildcards**）可用来代替该 `rule` 中 `input` 与 `output` 的具体内容。例如，在上面的例子中，`input` 和 `output` 分别代表了 `"data/article.txt"` 和 `"results/wordcount.txt"`。

如需做批处理，请灵活使用列表：

```
SAMPLES = ["A", "B", "C"]

rule all:
    input:
    	# 使用 expand 生成所有目标文件路径
    	# snakemake 可自行推断出 sample 的具体内容
        expand("results/{sample}.txt", sample=SAMPLES),

rule analyze:
    input:
        "data/{sample}.csv",
    output:
        "results/{sample}.txt",
    shell:
        "python analyze.py {input} > {output}",

```

## `run` 与 `shell`

若要执行 Python script，请使用 `run`：

```
rule split_fasta:
    input:
        fna="original/genome/genome123.fna"
    output:
        "split/{seq_id}.fa"
    run:
    	split(fna)

# 可在文件开头插入这个辅助函数。函数很短时，请在代码中内联匿名函数 lambda
def split(fna):
	pass
```

要在终端上执行，请使用 `shell`：

```
rule all:
    input:
        expand("results/{sample}.txt", sample=glob_wildcards("data/{sample}.csv").sample)

rule analyze:
    input:
        "data/{sample}.csv"
    output:
        "results/{sample}.txt"
    shell:
        "python3 analyze.py {input} > {output}"
    # 如果只是跑.py，也可换成“script”字段，例如
    # script:
    #	 "analyse.py"

```

## 参数

`params` 字段可填写指令需要输入的非文件参数：

```
# 用 DIAMOND 做 BLASTP
rule blast:
    input:
        query="prep.faa",
        database="prot.db"
    output:
        "results.f6"
    params:
    	evalue=1-e5,
    	id=30,
    	max_seqs=5
    shell:
        """
        ./diamond blastp -q {input.query} -d {input.database} -o {output} \
        --ultra-sensitive \
        --evalue {params.evalue} \
        --id {params.id} \
        --max-target-seqs {params.max_seqs} \
        --outfmt 6 \
        --threads 24 \
        --quiet
        """
```

## 资源分配

在允许使用多线程的情况下，Snakemake 能**自行将可并行任务分不同线程进行**，显著提高运行效率。 

要限制 Snakemake 使用的线程数，请在 `rule` 中使用 `threads` 字段。例如，并行化 AUGUSTUS 基因预测：

```
rule augustus_predict:
    input:
        "split/{seq_id}.fa"
    output:
        "augustus/{seq_id}.gff3"
    threads: 48
    shell:
        """
        augustus --species=tomato --gff3=on {input} > {output}
        """
```

`rule` 中的 `resources` 字段允许你进行更精细的资源配置：

```
rule augustus_predict:
    input:
        "split/{seq_id}.fa"
    output:
        "augustus/{seq_id}.gff3"
    threads: 48
    resources:
    	mem_mb = 120000
    shell:
        """
        augustus --species=tomato --gff3=on {input} > {output}
        """
```

## 提示信息与日志

若想在终端显示运行状态信息，请巧用 `message`：

```
rule name:
    input: "path/to/inputfile", "path/to/other/inputfile"
    output: "path/to/outputfile", "path/to/another/outputfile"
    message: "Executing somecommand with {threads} threads on the following files {input}."
    shell: "somecommand --threads {threads} {input} {output}"
```

要保存运行日志，请使用 `logs`。它可以将 `run`/`shell` 指令产生的所有日志信息写入到指定路径：

```
rule name:
    input: "path/to/inputfile"
    output: "path/to/outputfile"
    log: "logs/name.log"
    shell: "somecommand --log {log} {input} {output}"
```

## 模拟运行

`snakemake --lint` 可检查语法错误。

`snakemake --dry-run` （或者 `snakemake -n`）可查看 `Job stats` 以及每一个具体的 `job`；加 ` --printshellcmds`（`-p`）参数还可进一步查看将会执行的命令。

在实际运行前使用 `--dry-run`，可预防上机后可能发生的各种错误。

## 常见错误症状与解决方法

### `Error: cores have to be specified...`

**忘了加 `--cores` 参数。无论是否设置了 `resources` `threads` 等字段，都必须使用 `--cores`：**

``` 
snakemake --cores 1
```

### `WildcardError`

具体格式是

```
WildcardError in rule RULE in file "xxx.xxx", line 40:
Wildcards in params cannot be determined from output files. Note that you have to use a function to deactivate automatic wildcard expansion in params strings, e.g., `lambda wildcards: '{test}'`. Also see https://snakemake.readthedocs.io/en/stable/snakefiles/rules.html#non-file-parameters-for-rules: ......
'seq_id'
```

这是通配符出了问题。如果通配符出现了不一致，Snakemake 无法推断其具体内容，就会发生该报错。

第一行给出了错误发生位置，第三行给出了无法推断内容的通配符。**请检查这个通配符是否已知，或者是否可推断。**

两种可行案例是：

```
# Example 1
seq_id = ["1", "2", "3"]

......
	output:
		"{seq_id}.gff"

# Example 2
......
	input:
		"{seq_id}.gff3"
	output:
		"{seq_id}.gff"
```

### `IncompleteFilesException`

格式是

```
IncompleteFilesException:
The files below seem to be incomplete. If you are sure that certain files are not incomplete, mark them as complete with

    snakemake --cleanup-metadata <filenames>

To re-generate the files rerun your command with the --rerun-incomplete flag.
Incomplete files:
xxx.xxx
```

两种情况，分别处置：

- **如果是因为上次计算发生中断，结果不完整**，请在下次执行 `snakemake` 时，加 `--rerun-incomplete` 参数。
- **如果 `xxx.xxx` 确是经过完整计算的产物**，请先执行 `snakemake --cleanup-metadata xxx.xxx`，将其标记为 complete。

### 带 `ILP solver` 的橙色字警告 

原话是

`Failed to solve scheduling problem with ILP solver, falling back to greedy scheduler. You likely have to fix your ILP solver installation. Error message: PULP_CBC_CMD: Not Available (check permissions on cbc)`

这**并非致命错误**，不影响后续运行。

但因为从“Integer Linear Programming Solver”（ILP Solver）回退到性能更差的“Greedy Scheduler”（贪心算法），求解的速度会非常慢，表现为**复杂 `snakemake` 执行后要等待很久才能启动**。

最简单的方法是安装 `coincbc`：

`conda install -c conda-forge coincbc`

然后，在终端里进行测试：

```sh
$ python3
......
>> import pulp
>> solver = pulp.PULP_CBC_CMD(msg=True)
>> print(solver.available())
```

如果安装之后又出现莫名其妙的错误（特别是 `free(): invalid pointer` 这种奇葩），那就换 GLPK。它的速度肯定不如 cdc，但兼容性比 cdc 好很多：

`conda install -c conda-forge glpk`

然后测试

```sh
>> import pulp
>> solver = pulp.GLPK_CMD(msg=True)
>> print(solver.available())
```

> 如果使用 glpk 求解器，需要在 snakemake 命令里使用 `--scheduler-ilp-solver` 参数：
>
> `snakemake --cores all --scheduler-ilp-solver GLPK_CMD`

### 报错中出现 `line`

例如

```
NameError in file "xxx/xxx/xxx.xx", line 14:
name 'ids' is not defined
  File "xxx/xxx/xxx.xx", line 27, in <module>
  File "xxx/xxx/xxx.xx", line 14, in get_seq_ids
```

属于 Python 解释器报错。检查指定的行有没有语法错误。

## 其他

使用 Snakemake 后，请引用这篇论文：

[Mölder,  F., Jablonski, K.P., Letcher, B., Hall, M.B., Tomkins-Tinch, C.H.,  Sochat, V., Forster, J., Lee, S., Twardziok, S.O., Kanitz, A., Wilm, A.,  Holtgrewe, M., Rahmann, S., Nahnsen, S., Köster, J., 2021. Sustainable  data analysis with Snakemake. F1000Res 10, 33.](https://doi.org/10.12688/f1000research.29032.1)

该论文“滚动更新”，因此**无需考虑更换引用**。

想直观感受 Snakemake 的代码风格，请查阅

[https://snakemake.github.io/](https://snakemake.github.io/)；

官方教程详见

[https://snakemake.readthedocs.io/en/stable/tutorial/tutorial.html#tutorial](https://snakemake.readthedocs.io/en/stable/tutorial/tutorial.html#tutorial)。

目前我还没有整理 Snakemake 工作流模板，不过未来应该会更新。**如需查阅，请在这个网站里选择“Snakemake 模板”标签。**若模板存在问题无法运行，**请点击左侧面板最下方的那只“octo-cat”，带着报错信息提交 issue。**

