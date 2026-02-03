---
title: "有关pyproject.toml"
tags: [Python]
date: 2026-02-03 17:39 +0800
description: 还以为是什么新鲜东西。
categories: [Python]
---

[PEP-518](https://peps.python.org/pep-0518/) 的提出是为了解决当时软件包依赖项指定不规范的问题。10年来，这个 PEP 已经成为新 Python 软件包建立的基本范式，并为各种包管理器所接受。

那么，该 PEP 要求`pyproject.toml` 包含哪些内容？以及他们为何选择了 `.toml`，而不是 `.ini`、`yaml`、`.json`等其他格式？

## 选择 TOML 的理由

因为他们认为[“TOML 更加人类可读，且方便编辑”](https://peps.python.org/pep-0518/#file-format)：

>构建系统的依赖项将存储在名为 `pyproject.toml` 的文件中，该文件采用 TOML 格式编写。
>
>选择该格式的原因在于：它具备可读性（不同于 JSON），足够灵活（不同于 configparser），源自标准规范（同样区别于 configparser），且复杂度适中（不同于 YAML）。TOML 格式已被Rust社区用于其 Cargo 包管理器，私下邮件中也表明他们对选择 TOML 感到非常满意。

使用过其他文件格式作为配置文件的人，应该感受过它们带来的各种痛苦：

- JSON 不整齐的缩进与花括号令人不适，还不支持插入注释：

  ```json
  {
      "build": {
          "requires": [
              "setuptools",
              "wheel>=0.27"
          ]
      }
  }
  ```

- YAML 在 JSON 的基础上有所长进，但规范集非常之多（打印后多达 86 页），常用实现 PyYAML 不方便集成于 pip，以及对代码注入完全没有防御能力。

  ```yaml
  build:
      requires:
          - setuptools
          - wheel>=0.27
  ```

- INI（CFG）很接近 TOML，不过其实现 `configparser` 没有明确规范，不同版本之间难保证兼容性。说实话，我还是很喜欢 INI 的，特别是 `ExtendedInterpolation()` 扩展，在写复杂配置时会非常有帮助。

  ```ini
  [build]
  requires =
      setuptools
      wheel>=0.27
  ```

- 最后，则是 TOML。老实说，我不太认为 TOML 有哪门子创新——它似乎就是将同条目下的内容放进了一个类似列表的东西里。不过相比于完全没有规范集的 INI，TOML 算是更进步的。

  PEP-518 也在 INI 与 TOML 里反复横跳，但最后还是选择了 TOML。至于为什么，他们的理由是这样的：

  >"`setuptools` 采用的通用格式 `setup.cfg` 存在两个问题。其一是该文件采用 `.ini` 格式，正如上文 `configparser` 讨论中所提到的，此类文件存在诸多问题。其二是该文件的结构规范从未得到严格定义，因此无法确定未来采用何种格式才能确保安全，且不会对 `setuptools` 的安装过程造成潜在干扰。"

  ```toml
  [build-system]
  requires = ["setuptools"]
  ```

## pyproject.toml 的结构

经历了 PEP-518、517、621、660 等多次改进，目前 `pyproject.toml` 变成了这个样子：

>可能不太重要的说明：
>
>**PEP-517** 将构建系统与打包工具完全解耦，软件包构建再也不需要写 `setup.py`，而是让 pip 调用所谓的包构建接口。
>
>**PEP-621** 允许在 `pyproject.toml` 里直接写入项目元数据，包括项目名称、版本与相关依赖。
>
>**PEP-660** 将“可编辑安装”（`pip install -e .`）从 `setuptools` 剥离出来，从而供其他包管理系统实现。

### 构建系统（build-system）

其实就是编译 Python 软件包所需的工具。Python 最基本的打包工具是 `setuptools`，但根据项目需要，你可以选用其他工具作为打包器后端，例如我最喜欢的 `uv_build`。Rust/Python 跨语言开发者可能会很需要 `maturin`。

#### 样例 1：最基本的构建系统

```toml
[build-system]
requires = ["setuptools"]
```

#### 样例 2：使用 uv-build 作为后端的构建系统

```toml
[build-system]
requires = ["uv_build>=0.9.15,<0.10.0"]
build-backend = "uv_build"
```

### 项目元数据（project）

接下来就是*声明*（*declare*）你的项目元数据。该部分包含以下字段：

**项目名称**，也就是你这个的软件包的名字。该名称不区分大小写，且会忽略下划线、连字符、英文句点的类型与长度。例如，你可以将 `pip install cool-package` 中的 `cool-package` 替换为 `cool_package` `Cool-Package`，甚至 `CoOL-.-PackAge`，

**版本号**。版本号声明需符合“语义化”标准（SemVer）。以下是符合该标准的版本号样例 ：

- `0.1.0a3`（Alpha 版本 3）
- `0.1.0b4`（Beta 版本 4）
- `0.1.0rc5`（Release Candidate 版本 5）
- `0.1.0`（主版本号-次要版本号-修订版本号）

上述版本号是从上到下，逐级递进的（Alpha-Beta-RC-Final）。

另外，当 API 存在破坏性变更时，改动主版本号；增加新功能但仍可向下兼容时，改动次要版本号；只是对现有功能进行修复时，改动修订版本号。（不过在主版本号仍是 0 的情况下，任何改动都应该视作破坏性变更。）

Python 对版本号的规定比 SymVer 本身更加复杂，且考虑到各种嵌套情形，但上述这些已经足以应对多数情况。

如果有同时维护 `__version__` 字段的需求，请在 `__init__.py` 中设置 `__version__` 字段，并将 `version` 设置为 `dynamic`。此时，你只需要改动 `__init__.py` 里的 `__version__` 即可。

#### 样例 3：项目元数据的简单样例 

```toml
[project]
name = "spam-eggs"
version = "2020.0.0"
```

#### 样例 4：由构建系统自动获取项目版本号

```toml
[project]
name = "spam-eggs"
dynamic = ["version"]
```

**依赖关系**（dependencies and requirements）。它包含

- 必需依赖项（`dependencies`）；

- 可选依赖项（`optional-dependencies`），以及

- 所需的 Python 版本（`requires-python`）。

#### 样例 5：项目依赖于 Biopython（版本 1.86 及以上），且 Python 版本需大于 3.11

```toml
[project]
dependencies = ["biopython >= 1.86",]
requires-python = ">= 3.11"
```

#### 样例 6：可选配 GUI 版所需依赖

```toml
[project.optional-dependencies]
# 执行 pip install spam-eggs[gui] 才会安装的依赖
gui = ["PyQt5"]
```

**创建入口脚本**。如果你的软件包需要在系统内任意调用，可以考虑使用 `project-scripts`，它会在 Python 环境内的 `bin` 文件夹设置一个入口脚本。

#### 样例 7：设置软件包调用入口

```toml
[project.gui-scripts]
# 其含义是：先 `import spam`，再暴露可调用对象（这里则是一个叫 `main_gui()` 的函数）
# 这样一来，在命令行里执行 `spam-gui`，就会从这个入口脚本调用你所调用的函数
spam-gui = "spam:main_gui"
```

> 如果你更熟悉 `setup.py`，你可能会这样写：
>
> ```py
> # setup.py
> #!/usr/bin/env python
> # -*- coding: UTF-8 -*-
> 
> from setuptools import setup
> 
> # ......
> 
> setup(
>     entry_points={"gui-scripts": ["spam-gui = spam:main_gui",]},
> )
> ```
>
> 二者实质上是等同的。

**项目相关信息**，包括作者、简要描述、自述文件路径、项目标签、关键词、许可证等信息。具体请看样例  8。

#### 样例 8：一个较完整的项目信息说明

```toml
[project]
# 项目作者
authors = [{name = "Someone Here", email = "someone@example.com"}]

# 如果项目作者只有一个人，可直接填写 author 和 author_email 字段
# author = "Someone Here"
# author_email = "someone@example.com"

# 项目维护者
maintainers = [{name = "Another One Here", email = "another@example.com"}]

# 一句话描述
description = "I LIKE JUNKY!!!"

# 自述文件位置
readme = "README.md"

# 许可证（license）及其文件路径（license-files）
# 许可证名称需符合 SPDX 规范
# 许可证文件路径可使用正则表达式
license = "GPL-3.0-only"
license-files = "LICEN[CS]E*"

# 项目关键词
keywords = ["egg", "bacon", "sausage", "tomatoes", "Lobster Thermidor"]

# 项目标签
# 会显示在 PyPi 上，以供分类搜索
# 具体请参考：https://pypi.org/classifiers
classifiers = [
  # 项目是否成熟？或者是否已经不再维护？
  # 可能的选项包括
  #   3 - Alpha
  #   4 - Beta
  #   5 - Production/Stable
  "Development Status :: 4 - Beta",

  # 要面向哪些人群？或者适用于哪些领域？
  "Intended Audience :: Developers",
  "Topic :: Software Development :: Build Tools",

  # 使用了哪些语言？或者支持哪些 Python 版本？
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.6",
  "Programming Language :: Python :: 3.7",
  "Programming Language :: Python :: 3.8",
  "Programming Language :: Python :: 3.9",
]

# 项目网站，例如项目主页、文档页或论坛页
[project.urls]
Homepage = "https://example.com"
"Download Link" = "https://example.com/abc.tar.gz"
Documentation = "https://readthedocs.org"
Repository = "https://github.com/me/spam.git"
"Bug Tracker" = "https://github.com/me/spam/issues"
Changelog = "https://github.com/me/spam/blob/master/CHANGELOG.md"
```

## uv、pytest 与 maturin 的额外说明

考虑到不少人也有使用 uv、pytest，或者 maturin，而这些并未在“打包指南”中特别指出，因此值得在此强调说明。

`pyproject.toml` 可通过 `uv init` 直接生成，**uv** 配置则位于该文件的 `[tool.uv]` 处，包括：

#### 样例 9：常见的 uv 配置

```toml
[[tool.uv.index]]
name = "spam-eggs"
url = "https://test.pypi.org/simple/"
publish-url = "https://test.pypi.org/legacy/"
explicit = true
```

其中的 `[[]]` 是 TOML 的表数组写法。上面这个配置等价于 JSON 的

```json
{
    "tool": {
        "uv": {
            "index": [
                {"name": "spam-eggs"},
                {"url": "https://test.pypi.org/simple/"},
                {"publish-url": "https://test.pypi.org/legacy/"},
                {"explicit": true}
            ]
        }
    }
}
```

如有必要，可写在 `uv.toml` 文件里，不过这种在全局设定上更常用（例如 `~/.config/uv/uv.toml`）。当你想使用 PyPi 镜像时，这会非常有用。

#### 样例 10：设置 uv 使用的 PyPi 镜像

```toml
# ~/.config/uv/uv.toml
[[index]]
url = "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple/"
default = true
```

要使用 uv 的打包后端，请务必在 `[build-system]` 里说明（见样例 2）。

----

对于 **pytest**，其设定同样有个独立位置：`[tool.pytest]`：

#### 样例 11：常见的 pytest 配置（INI 风格）

```toml
[tool.pytest.ini_options]
# pytest 所需的最低版本
minversion = "7.0"

# 运行参数
addopts = """
-ra -q
"""

# 单元测试脚本路径
testpaths = ["tests"]
```

#### 样例 12：常见的 pytest 配置（原生 TOML 风格，需 pytest 9.0 及以上版本）

```toml
[tool.pytest]
minversion = "9.0"
addopts = ["-ra", "-q"]
testpaths = ["tests"]
```

如果需计算测试覆盖率，请确保在 CI 时安装 `pytest-cov` 与 `coverage`。

#### 样例 13：包含覆盖率统计的 pytest 配置（INI 风格）

```toml
[tool.pytest.ini_options]
minversion = "7.0"
addopts = """
-ra
--strict-markers
--cov=spam-eggs
--cov-report=term-missing
--cov-branch
--cov-report=xml
--junitxml=junit.xml
-o
junit_family=legacy
"""
testpaths = ["tests"]

[tool.coverage.run]
branch = true
source = ["spam-eggs"]

[tool.coverage.report]
show_missing = true
fail_under = 80
exclude_lines = ["pragma: no cover",]
```

具体请见 [pytest](https://docs.pytest.org/en/stable/reference/customize.html) 与 [coverage](https://coverage.readthedocs.io/en/7.13.2/config.html) 的文档。

----

使用 Rust/Python 交叉开发的程序员，一定离不开 **maturin**。此时你不仅需要在 `pyproject.toml` 里插入工具配置（`[tool.maturin]`），还要在 `[build-system]` 里设置打包后端。

#### 样例 14：适用于 maturin 的 pyproject.py 配置

```toml
[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

[tool.maturin]
profile = "release"
bindings = "cffi"
compatibility = "linux"
```

[maturin 文档](https://www.maturin.rs/config.html) 对此有非常详细的说明。

对于 Cargo 包名、Wheel 包名、import 名混杂的问题，Cargo 和 Wheel 包的名称由各自的项目配置文件（`cargo.toml` 与 `project.toml`）决定，import 名则来自包目录的结构（`./src/import_name`）；由 maturin 编译出来的包则总是使用 import 名——这与纯 Python 下调用自己软件包里的程序是同样道理。

