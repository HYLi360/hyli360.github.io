---
title: "解决PAML密码子表索引问题"
tags:
  - PAML
  - 杂谈
date: 2025-12-20 14:46:33 +0800
description: "PAML的密码子表采用与NCBI GenBank不同的索引顺序，而Biopython基于NCBI GenBank密码子表的索引，使用起来较为不便。"
categories: PAML
---

NCBI GenBank 密码子表分类有接近 30 种，不过最常用的还是这些：

```
1. 标准密码子
2. 植物线粒体密码子
3. 酵母线粒体密码子
4. 霉菌、原生动物和腔肠动物线粒体密码子及支原体/螺原体密码子
5. 无脊椎动物线粒体密码子
9. 棘皮动物与扁形动物线粒体密码子
11. 细菌、古菌与植物质体密码子
```

而根据 [PAML Wiki](https://github.com/abacus-gene/paml/wiki/yn00)，他们的密码子表从 `0` 到 `10`，分为 11 个类别：

```
0: universal.               # 通用
1: mammalian mt.            # 哺乳动物线粒体
2: yeast mt.                # 酵母线粒体
3: mold mt.                 # 霉菌线粒体
4: invertebrate mt.         # 无脊椎动物线粒体
5: ciliate nuclear.
6: echinoderm mt.
7: euplotid mt.
8: alternative yeast nu.    # 替代酵母细胞核
9: ascidian mt.
10: blepharisma nu.
```

可见它们并非按顺序一一对应的关系。

---

不过为何密码子表如此重要？因为不同生物类群的密码子表在起始密码子、终止密码子，以及密码子与氨基酸的对应关系有些许的不同。例如，这是最经典的，适用于大多数生物细胞核的密码子表：

```
TTT F Phe      TCT S Ser      TAT Y Tyr      TGT C Cys  
TTC F Phe      TCC S Ser      TAC Y Tyr      TGC C Cys  
TTA L Leu      TCA S Ser      TAA * Ter      TGA * Ter  
TTG L Leu i    TCG S Ser      TAG * Ter      TGG W Trp  

CTT L Leu      CCT P Pro      CAT H His      CGT R Arg  
CTC L Leu      CCC P Pro      CAC H His      CGC R Arg  
CTA L Leu      CCA P Pro      CAA Q Gln      CGA R Arg  
CTG L Leu i    CCG P Pro      CAG Q Gln      CGG R Arg  

ATT I Ile      ACT T Thr      AAT N Asn      AGT S Ser  
ATC I Ile      ACC T Thr      AAC N Asn      AGC S Ser  
ATA I Ile      ACA T Thr      AAA K Lys      AGA R Arg  
ATG M Met i    ACG T Thr      AAG K Lys      AGG R Arg  

GTT V Val      GCT A Ala      GAT D Asp      GGT G Gly  
GTC V Val      GCC A Ala      GAC D Asp      GGC G Gly  
GTA V Val      GCA A Ala      GAA E Glu      GGA G Gly  
GTG V Val      GCG A Ala      GAG E Glu      GGG G Gly  
```

> 注：标 `i` 的为起始密码子，标 `*` 和 `Ter` 的是终止密码子。

更简洁的表示方式，是这样：

```
    AAs  = FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG
  Starts = ---M------**--*----M---------------M----------------------------
  Base1  = TTTTTTTTTTTTTTTTCCCCCCCCCCCCCCCCAAAAAAAAAAAAAAAAGGGGGGGGGGGGGGGG
  Base2  = TTTTCCCCAAAAGGGGTTTTCCCCAAAAGGGGTTTTCCCCAAAAGGGGTTTTCCCCAAAAGGGG
  Base3  = TCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAG
```

> 注：标 `M` 的为起始密码子，标 `*` 的为终止密码子。
>
> 这种表应当按列查看——例如第一列的密码子是 `TTT`，此时翻译出的氨基酸为 `F`，即 `Phe`。

深扒 PAML 源码后发现，在 `tool.c` 也硬编码了一系列的密码子表，不过估计是为了性能优化，采用数字索引的方法表示不同密码子与氨基酸的对应关系。例如：

```c
char BASEs[] = "TCAGUYRMKSWHBVD-N?";
char *EquateBASE[] = { "T","C","A","G", "T", "TC","AG","CA","TG","CG","TA",
     "TCA","TCG","CAG","TAG", "TCAG","TCAG","TCAG" };
char CODONs[256][4];
char AAs[] = "ARNDCQEGHILKMFPSTWYV-*?X";
char nChara[256], CharaMap[256][64];
char AA3Str[] = { "AlaArgAsnAspCysGlnGluGlyHisIleLeuLysMetPheProSerThrTrpTyrVal***" };
char BINs[] = "TC";
int GeneticCode[][64] =
{ {13,13,10,10,15,15,15,15,18,18,-1,-1, 4, 4,-1,17,
  10,10,10,10,14,14,14,14, 8, 8, 5, 5, 1, 1, 1, 1,
   9, 9, 9,12,16,16,16,16, 2, 2,11,11,15,15, 1, 1,
  19,19,19,19, 0, 0, 0, 0, 3, 3, 6, 6, 7, 7, 7, 7}, /* 0:universal */
   ......}
```

横向顺序与简化版密码子表示法的顺序相一致，都是按 `T->C->A->G` 的顺序从最后面替换到最前面；数字代表其氨基酸索引，例如 `13` 可索引至 `AAs` 的 `F`，以及 `AA3Str` 的 `Phe`（ `[index*3:index*3+3]` ）。如果是 `-1`，则表示根本没有这个氨基酸，也就是终止密码子的意思了。

至于为啥 `AAs` 不按字母顺序排列？因为实际上它是按“三字母缩写” `AA3Str` 来排序的。这多少令人摸不着头脑......

---

想解码它其实非常轻松，使用 Python 的 REPL 就能解决：

```py
>>> # 这些直接从源码上拷贝下来就行
>>> AAs = "ARNDCQEGHILKMFPSTWYV-*?X"
>>> idx_list_0 = [13,13,10,10,15,15,15,15,18,18,-1,-1, 4, 4,-1,17,
...   10,10,10,10,14,14,14,14, 8, 8, 5, 5, 1, 1, 1, 1,
...    9, 9, 9,12,16,16,16,16, 2, 2,11,11,15,15, 1, 1,
...   19,19,19,19, 0, 0, 0, 0, 3, 3, 6, 6, 7, 7, 7, 7]
>>> buffer=[]
>>> for i in idx_list_0:
...     if i == -1:
...         buffer.append("*")
...     else:
...         buffer.append(AAs[i])
...         
>>> "".join(buffer)
'FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG'
```

他那个表，最大的缺点就是——不知道谁是起始密码子！不过其实只要把终止密码子确定到就行，cDNA 不太需要确定这个玩意。

继续：

```py
>>> idx_list_1 = [13,13,10,10,15,15,15,15,18,18,-1,-1, 4, 4,17,17,
...   10,10,10,10,14,14,14,14, 8, 8, 5, 5, 1, 1, 1, 1,
...    9, 9,12,12,16,16,16,16, 2, 2,11,11,15,15,-1,-1,
...   19,19,19,19, 0, 0, 0, 0, 3, 3, 6, 6, 7, 7, 7, 7]
>>> 
>>> buffer=[]
>>> for i in idx_list_1:
...     if i == -1:
...         buffer.append("*")
...     else:
...         buffer.append(AAs[i])
...         
>>> "".join(buffer)
'FFLLSSSSYY**CCWWLLLLPPPPHHQQRRRRIIMMTTTTNNKKSS**VVVVAAAADDEEGGGG'
```

与 Table 2 完美对应：

```
    AAs  = FFLLSSSSYY**CCWWLLLLPPPPHHQQRRRRIIMMTTTTNNKKSS**VVVVAAAADDEEGGGG
  Starts = ----------**--------------------MMMM----------**---M------------
  Base1  = TTTTTTTTTTTTTTTTCCCCCCCCCCCCCCCCAAAAAAAAAAAAAAAAGGGGGGGGGGGGGGGG
  Base2  = TTTTCCCCAAAAGGGGTTTTCCCCAAAAGGGGTTTTCCCCAAAAGGGGTTTTCCCCAAAAGGGG
  Base3  = TCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAG
```

综上，我们获得了 icode 从 0 到 10 与 NCBI GenBank 密码子表的对应关系表：

| `icode`     | `Transl Table` |
| ------------------|------------------------------------------- |
| `0` universal        | `1` The Standard Code                                            |
| `1` vertebrate mt.   | `2` The Bacterial, Archaeal and Plant Plastid Code |
| `2` yeast mt.        | `3` The Yeast Mitochondrial Code                                 |
| `3` mold mt.         | `4` The Mold, Protozoan, and Coelenterate Mitochondrial Code and the Mycoplasma/Spiroplasma Code |
| `4` invertebrate mt. | `5` The Invertebrate Mitochondrial Code                          |
| `5` ciliate nuclear  | `6` The Ciliate, Dasycladacean and Hexamita Nuclear Code         |
| `6` echinoderm mt.  | `9` The Echinoderm and Flatworm Mitochondrial Code |
| `7` euplotid mt.     | `10` The Euplotid Nuclear Code |
| `8` alternative yeast nu. | `12` The Alternative Yeast Nuclear Code |
| `9` ascidian mt.     | `13` The Ascidian Mitochondrial Code |
| `10` blepharisma nu. | `15` Blepharisma Nuclear Code |

使用一个字典来表示这种映射：

```py
NCBI_TO_PAML_ICODE = {
    1:0,   "Standard":0,
    2:1,   "Vertebrate Mt":1, 
    3:2,   "Yeast Mt":2,
    4:3,   "Mold Mt":3,
    5:4,   "Invertebrate Mt":4,
    6:5,   "Ciliate Nucl":5,
    9:6,   "Echinoderm Mt":6,
    10:7,  "Euplotid Nucl": 7,
    12:8,  "Alternative Yeast Nucl":8,
    13:9,  "Ascidian Mt":9,
    15:10, "Blepharisma Nucl":10,
}
```

