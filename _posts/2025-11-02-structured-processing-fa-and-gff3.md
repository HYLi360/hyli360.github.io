---
title: "使用BioPython处理FASTA/GFF文件"
tags: [bioinfo-tools]
date: 2025-11-02 12:08:15 +0800
description: "Python中，处理.fna/.faa（FASTA）的功能由BioPython实现；处理.gff3（GFF3）的功能由BioPython库的扩展库BCBio.gff实现。"
categories: [生物信息学, 工具]
---

## 处理 FASTA 文件

```py
from Bio import SeqIO

records = list(SeqIO.parse("Vvi_Genome.fa", "fasta"))
for rec in records:
    # 每一个 record 都是一个完整的 SeqRecord 对象
    print(rec.id, rec.description, len(rec.seq))

"""
1 1 Vitis vinifera cultivar Pinot Noir 40024 chromosome 1, ASM3070453v1 27822162
2 2 Vitis vinifera cultivar Pinot Noir 40024 chromosome 2, ASM3070453v1 20941263
3 3 Vitis vinifera cultivar Pinot Noir 40024 chromosome 3, ASM3070453v1 21317290
......
"""
```

更加 modern、fast，且 pythonic 的方法，是使用枚举 `enumerate`：

```py
from Bio import SeqIO

for idx, rec in enumerate(SeqIO.parse("Vvi_Genome.fa", "fasta")):
    print(idx, rec.id, rec.description, len(rec.seq))

"""
0 1 1 Vitis vinifera cultivar Pinot Noir 40024 chromosome 1, ASM3070453v1 27822162
1 2 2 Vitis vinifera cultivar Pinot Noir 40024 chromosome 2, ASM3070453v1 20941263
2 3 3 Vitis vinifera cultivar Pinot Noir 40024 chromosome 3, ASM3070453v1 21317290
......
"""
```

---

在 `fasta` 中，真正常用有用的是这些字段：

- `id`，也就是 `>` 后的第一个字段。可改。

  ```py
  from Bio import SeqIO
  
  for idx, rec in enumerate(SeqIO.parse("Vvi_Genome.fa", "fasta")):
      rec.id = "Chr" + str(idx+1)
      print(idx, rec.id, rec.description, len(rec.seq))
  
  """
  0 Chr1 1 Vitis vinifera cultivar Pinot Noir 40024 chromosome 1, ASM3070453v1 27822162
  1 Chr2 2 Vitis vinifera cultivar Pinot Noir 40024 chromosome 2, ASM3070453v1 20941263
  2 Chr3 3 Vitis vinifera cultivar Pinot Noir 40024 chromosome 3, ASM3070453v1 21317290
  ......
  """
  ```

- `description`，即 `>` 行去掉 `>` 的部分（含 `rec.id`）。可改。

  ```py
  from Bio import SeqIO
  
  for idx, rec in enumerate(SeqIO.parse("Vvi_Genome.fa", "fasta")):
      rec.description = "Chr" + str(idx+1) + " Grape_Ref_Genome_ASM3070453v1"
      print(idx, rec.id, rec.description, len(rec.seq))
      
  """
  0 1 Chr1 Grape_Ref_Genome_ASM3070453v1 27822162
  1 2 Chr2 Grape_Ref_Genome_ASM3070453v1 20941263
  2 3 Chr3 Grape_Ref_Genome_ASM3070453v1 21317290
  ......
  """
  ```

- `annotations`，即注释，以字典“键-值对”形式呈现。可改，可补充，但不会显示在 `>` 行。

- `seq`，序列信息。也可改，但现在暂时没有用处。

想写回并验证结果，请使用 `SeqIO.write`。

```py
from Bio import SeqIO

new_record = []

for idx, rec in enumerate(SeqIO.parse("Vvi_Genome.fa", "fasta")):
    rec.id = "Chr" + str(idx+1)
    print(idx, rec.id, rec.description, len(rec.seq))
    new_record.append(rec)

SeqIO.write(new_record, "out.fna", "fasta")
```

可见 `>` 行已经被改动。不过并非破坏性，只是将原有字段向后错开而已。

```
>Chr1 1 Vitis vinifera cultivar Pinot Noir 40024 chromosome 1, ASM3070453v1
```

不过，如果想让输出更“干净”，可以在 `append` 前请清空 `description`（`rec.description=""`）。

```py
from Bio import SeqIO

new_record = []

for idx, rec in enumerate(SeqIO.parse("Vvi_Genome.fa", "fasta")):
    rec.id = "Chr" + str(idx+1)
    rec.description = ""
    print(idx, rec.id, rec.description, len(rec.seq))
    new_record.append(rec)

SeqIO.write(new_record, "out.fna", "fasta")

"""
>Chr1
>Chr2
>Chr3
......
"""
```

## 处理 GFF3 文件

`BioPython` 并没有对 GFF3 格式的完备实现；但它的其中一个扩展库—— [`BCBio.GFF`](https://github.com/chapmanb/bcbb/tree/master/gff)，可以实现对 GFF3 格式文件的各种操作。

bcbio-gff 由 BioPython 的开发者之一 Brad Chapman 独立开发并维护，其实现正是基于 BioPython 提供的各类核心对象。

---

GFF3 “基本上”算是一个标准的 TSV（Tab-Separated Values）文件，理论上可直接使用 Pandas 读取；

但问题在于，第 9 列（Attribute）包含着一个树状的关系结构，因此每一行的关系并不平等。这一点单用 Pandas 很难表现出来。

所以，在处理 GFF3 文件之前，做一些检查是非常有必要的。`GFFExaniner` 就提供了检查 GFF 文件的实现，其中一个功能（`parent_child_map`），就是检查文件内各行的关系结构，即各 feature 的 `type`、`source` 与 `Parent` 关系：

```py
import pprint
from BCBio.GFF import GFFExaminer

examiner = GFFExaminer()
with open("Vvi_Genome.gff3") as f:
    pprint.pprint(examiner.parent_child_map(f))
```

输出为

```
{('BestRefSeq', 'gene'): [('BestRefSeq', 'lnc_RNA'),
                          ('BestRefSeq', 'mRNA'),
                          ('BestRefSeq', 'primary_transcript')],
 ('BestRefSeq', 'lnc_RNA'): [('BestRefSeq', 'exon')],
 ('BestRefSeq', 'mRNA'): [('BestRefSeq', 'CDS'), ('BestRefSeq', 'exon')],
 ('BestRefSeq', 'miRNA'): [('BestRefSeq', 'exon')],
 ('BestRefSeq', 'primary_transcript'): [('BestRefSeq', 'exon'),
                                        ('BestRefSeq', 'miRNA')],
 ('BestRefSeq', 'pseudogene'): [('BestRefSeq', 'transcript')],
 ('BestRefSeq', 'transcript'): [('BestRefSeq', 'exon')],
 ('BestRefSeq%2CGnomon', 'gene'): [('BestRefSeq', 'mRNA'),
                                   ('Gnomon', 'mRNA'),
                                   ('Gnomon', 'transcript')],
 ('Gnomon', 'gene'): [('Gnomon', 'lnc_RNA'),
                      ('Gnomon', 'mRNA'),
                      ('Gnomon', 'transcript')],
 ('Gnomon', 'lnc_RNA'): [('Gnomon', 'exon')],
 ('Gnomon', 'mRNA'): [('Gnomon', 'CDS'), ('Gnomon', 'exon')],
 ('Gnomon', 'pseudogene'): [('Gnomon', 'exon'), ('Gnomon', 'transcript')],
 ('Gnomon', 'transcript'): [('Gnomon', 'exon')],
 ('cmsearch', 'gene'): [('cmsearch', 'rRNA'),
                        ('cmsearch', 'snRNA'),
                        ('cmsearch', 'snoRNA')],
 ('cmsearch', 'pseudogene'): [('cmsearch', 'exon')],
 ('cmsearch', 'rRNA'): [('cmsearch', 'exon')],
 ('cmsearch', 'snRNA'): [('cmsearch', 'exon')],
 ('cmsearch', 'snoRNA'): [('cmsearch', 'exon')],
 ('tRNAscan-SE', 'gene'): [('tRNAscan-SE', 'tRNA')],
 ('tRNAscan-SE', 'tRNA'): [('tRNAscan-SE', 'exon')]}
```

它的输出是一个嵌套了字典、元组、列表的复杂字典。你可以不用 `pprint`，只是输出不会更简单，可读性还会变差。

它的功能？一方面是**确定这个 GFF 文件存在哪些字段**（例如 mRNA、transcript）；另一方面它还可以**提供获得这些结果所使用的工具**（`BestRefSeq` 来自 NCBI RefSeq、`Gnomon` 来自 Gnomon plane、`cmsearch` 来自 Infernal）。

另一方面，使用 `avaliable_limits` 可清楚展现了各字段 （`gff_id`、`gff_source`、`gff_source_type`、`gff_type`）的所有取值及数量，这一点对解析文件也很重要：

```py
import pprint
from BCBio.GFF import GFFExaminer

examiner = GFFExaminer()
with open("Vvi_Genome.gff3") as f:
    pprint.pprint(examiner.available_limits(f))

"""
{'gff_id': {('1',): 37823,
            ('10',): 32511,
            ('11',): 29325,
            ......},
 'gff_source': {('BestRefSeq',): 6625,
                ('BestRefSeq%2CGnomon',): 113,
                ('Curated Genomic',): 5,
                ......},
  ......
"""
```

`avaliable_limits` 比 `parent_child_map` 似乎好用很多。

---

确定了 GFF3 文件的逻辑结构，接下来就可以解析文件本身了。解析的方法基本一致，也是使用 `parse`：

```py
from BCBio import GFF

with open("Vvi_Genome.gff3") as f:
    for rec in enumerate(GFF.parse(f)):
        print(rec)

"""
(0, SeqRecord(seq=Seq(None, length=27822162), id='1', name='<unknown name>', description='<unknown description>', dbxrefs=[]))
(1, SeqRecord(seq=Seq(None, length=27504061), id='10', name='<unknown name>', description='<unknown description>', dbxrefs=[]))
(2, SeqRecord(seq=Seq(None, length=20048508), id='11', name='<unknown name>', description='<unknown description>', dbxrefs=[]))
......
"""
```

使用 `limit_info` 字典可筛选出指定范围的 feature，**可用字段与 `avaliable_limits` 的输出结果一致。**

```py
from BCBio import GFF

limit_info = {"gff_id": "1"}

with open("Vvi_Genome.gff3") as f:
    for rec in enumerate(GFF.parse(f, limit_info=limit_info)):
        print(rec)

"""
(0, SeqRecord(seq=Seq(None, length=27822162), id='1', name='<unknown name>', description='<unknown description>', dbxrefs=[]))
"""
```

`target_lines` 用来限制解析器每次读取的行数，在小内存机器上尤其适用。虽然理论上不会因为行数限制而截断 feature，但不会限制得太低，到 10000 行就足够了。

```py
from BCBio import GFF

with open("Vvi_Genome.gff3") as f:
    for idx, rec in enumerate(GFF.parse(f, target_lines=10000)):
        print(rec)
```

---

最后是修改与写回的问题。改动的方法与 fasta 的几乎完全一样，唯一需要做的只是显式执行 `open`：

```py
from BCBio import GFF

with open("Vvi_Genome.gff3") as f:
    for idx, rec in enumerate(GFF.parse(f)):
        rec.id = "Chr" + str(rec.id)
        print(rec)
```

写回则再执行一次 `open`。

```py
from BCBio import GFF

new_record = []

with open("Vvi_Genome.gff3") as file_in, open("Vvi_Genome_changed.gff3", "w") as file_out:
    for rec in GFF.parse(file_in):
        rec.id = "Chr" + str(rec.id)
        new_record.append(rec)
    GFF.write(new_record, file_out)
```

## 同时修改 FNA 与 GFF3 的染色体编号

从公共数据库下载到的基因组数据采用不同的编号规则，直接用来作图可能不太美观。因此，最好还是把染色体编号改一下。

做一下 `cat genome.fna | grep ">"` 就可以查看有哪些染色体了。

然后将原染色体编号放在一侧，打一个 Tab，在另一侧写上新的染色体编号。

```
CM009654.1	Chr01
CM009655.1	Chr02
CM009656.1	Chr03
CM009657.1	Chr04
CM009658.1	Chr05
......
```

最后跑一下脚本就 OK 了。

```PY
import argparse

from Bio import SeqIO
from BCBio import GFF

# 生成染色体替换字典
def switch_dict(map_path: str) -> dict:
    dictionary = {}
    with open(map_path, "r") as map:
        for line in map:
            line_ls = line.strip().split("\t")
            dictionary[line_ls[0]] = line_ls[1]
    return dictionary

def main():
    print()
    parser = argparse.ArgumentParser(description="Renaming the chromosome name in fna/gff3 file.")

    parser.add_argument('--infna', required=True, help='Input FNA file name.')
    parser.add_argument('--ingff', required=True, help='Input GFF3 file name.')
    parser.add_argument('--inmap', required=True, help='Old and new Chr name, in TSV format.')
    parser.add_argument('--outfna', required=False, help='Output FNA file name. Optional.')
    parser.add_argument('--outgff', required=False, help='Output GFF3 file name. Optional.')

    # 生成参数。如无，在文件名后加 `_changed`
    args = parser.parse_args()
    outfna = args.outfna if args.outfna else args.infna.replace('.', '_changed.')
    outgff = args.outgff if args.outgff else args.ingff.replace('.', '_changed.')

    # 初始化
    d = switch_dict(args.inmap)
    fna_record = []
    gff_record = []
    
    # 更改 FNA
    for idx, rec in enumerate(SeqIO.parse(args.infna, "fasta")):
        # 改名；若无对应则保持原状
        try: rec.id = d[rec.id]
        except KeyError: rec.id = rec.id
        # 添加记录
        fna_record.append(rec)
        print("FNA", idx+1, rec.id)
    # 写入
    SeqIO.write(fna_record, outfna, "fasta")

    # 更改 GFF3。只是额外使用 open 而已
    with open(args.ingff) as gff_original, open(outgff, "w+") as gff_changed:
        for idx, rec in enumerate(GFF.parse(gff_original)):
            # 同上
            try: rec.id = d[rec.id]
            except KeyError: rec.id = rec.id
            # 防注释输入后生成乱码
            rec.annotations.pop("sequence-region", None)
            rec.annotations.pop("gff-version", None)
            gff_record.append(rec)
            print("GFF3", idx+1, rec.id)
        # 写入
        GFF.write(gff_record, gff_changed)
    
    print("DONE!")

if __name__ == "__main__":
    main()
```

