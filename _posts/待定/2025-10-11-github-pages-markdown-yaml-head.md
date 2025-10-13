# **Linux杂谈1：在文件系统做设备管理**

在Windows上，不同存储设备/分区是通过盘符（`C:`、`D:`、......）区分的；但到了Linux这里，没有所谓“C盘”“D盘”，而是一个个目录——例如存放用户自己文件的 `/home` 目录，存放通用资源的 `/usr` （**不是`/user`！！！**），还有挂载设备的 `/mnt` 与 `/media`......

Linux，甚至UNIX-like系统的设计哲学，都是**“一切皆文件”**：哪怕你是个CD机，是硬盘盒，甚至是网卡和打印机，它们在文件系统里都有自己的位置。贝尔实验室的UNIX无疑是这个理念的一种实现，但后继者“Plan 9”系统做的则更加彻底——不仅一切皆文件，**任何设备都可以挂载到文件树上**，供用户任意使用。（但这就是个很长的故事了：简单来说，Plan 9差点取代了Linux*操作系统*，如今屈身为其他系统服务，成为Unix式的*文件管理系统*......）

——废话不再讲了。我们就用实证的方法，来探索文件系统上的各种设备吧。

我这台电脑安装的是Ubuntu 24.04 LTS，因个人需求将桌面环境换成KDE Plasma（所以也有人笑称，这是“手工版”的Kubuntu。我对此欣然接受）。可以看到，电脑上的所有设备，都在 `/dev` 这个目录下（但**文件夹里的不算**，我们之后再解释原因）。

![image-20250831174734719](asset/img/Linux1/image-20250831174734719.png)

## 块设备

在Unix-like的语境下，“块设备”是任何以“块”方式存储数据的设备，包括而不限于硬盘、软盘、U盘、SD卡、光驱、内存之类。它们无疑和文件系统关系更加密切——从文件系统里找到可存储设备，读取或者写入数据。很合理的嘛！

它们有个共同点：在 `ls -l` 里以 `b`（_block_）开头。

```
brw-rw----   1 root disk    259,     0  8月 30 14:32 nvme0n1
brw-rw----   1 root disk    259,     1  8月 30 14:32 nvme0n1p1
brw-rw----   1 root disk    259,     2  8月 30 14:32 nvme0n1p2
brw-rw----   1 root disk    259,     3  8月 30 14:32 nvme0n1p3
brw-rw----   1 root disk    259,     4  8月 30 14:32 nvme1n1
brw-rw----   1 root disk    259,     5  8月 30 14:32 nvme1n1p1
brw-rw----   1 root disk    259,     6  8月 30 14:32 nvme1n1p5
```

对于这里的 `nvme` 硬盘（我使用的是固态硬盘，走的nvme协议，因此Linux将它当作nvme设备），我们看到有三个数字：

- `nvmeX` -> 表示这是第X个nvme设备；
- `nY` -> 表示这是该设备的第Y个命名空间；
- `pZ`-> 表示这是该命名空间下的第Z个分区。

如果你的电脑支持插内存卡（这一般是创作用笔记本电脑的功能），或者是带eMMC芯片（......那得是相当老的平板才有的了），你会看到 `mmcblk0p1`，它代表着这是第0个mmc设备的第1个分区。

```
brw-rw----   1 root disk    179,     0  9月  1 01:30 mmcblk0
brw-rw----   1 root disk    179,     1  9月  1 01:30 mmcblk0p1
```

更常见的，如果你用的是机械硬盘，或者走SCSI协议的固态（常见于可移动硬盘），就会看到 `sda/b/c/d`，后面跟着数字。意思跟上面的差不多：第0/1/2/3个SCSI设备（更具体地说，是“大容量存储设备”）上的第N个分区。

```
brw-rw----   1 root disk      8,     0  9月  1 01:30 sda
brw-rw----   1 root disk      8,     1  9月  1 01:30 sda1
brw-rw----   1 root disk      8,    16  9月  1 01:30 sdb
brw-rw----   1 root disk      8,    17  9月  1 01:30 sdb1
brw-rw----   1 root disk      8,    18  9月  1 01:30 sdb2
```

不过，**数量真正称得上“多”的块设备**，其实都是这些：

```
brw-rw----   1 root disk      7,     0  8月 30 14:32 loop0
brw-rw----   1 root disk      7,     1  8月 30 14:32 loop1
brw-rw----   1 root disk      7,    10  8月 30 14:32 loop10
brw-rw----   1 root disk      7,    11  8月 30 14:32 loop11
brw-rw----   1 root disk      7,    12  8月 30 14:32 loop12
brw-rw----   1 root disk      7,    13  8月 30 14:32 loop13
brw-rw----   1 root disk      7,    14  8月 30 14:32 loop14
brw-rw----   1 root disk      7,    15  8月 30 14:32 loop15
brw-rw----   1 root disk      7,    16  8月 30 14:32 loop16
brw-rw----   1 root disk      7,    17  8月 30 14:32 loop17
brw-rw----   1 root disk      7,    18  8月 30 14:32 loop18
brw-rw----   1 root disk      7,    19  8月 30 14:32 loop19
```

一群**loop**！它们并不对应任何物理设备（即**伪设备**）；但如果某些文件要像设备那样挂载到文件系统上（例如挂载 `.qcow2`，或者 `.iso` 文件），就需要这些“替身”上场了。

<img src="asset/img/Linux1/image-20250831175337636.png" alt="image-20250831175337636"/>

> 将Manjaro（一种基于Arch Linux的Linux发行版）系统镜像挂载到 `/cdrom`（`mount manjaro.iso /cdrom`），可以看到其“挂载来源”位于 `/dev/loop32`。一般情况下，里面的文件可以读取，可以复制到其他设备，也可以执行 `umount /dev/loop32`（或者 `umount /cdrom`） 解除挂载，但无法被修改。

> **NOTE**
>
> Q：`/cdrom` 能挂载光盘这我知道，但 `/mnt` 和 `/media` 可以挂载谁？有没有需要遵循的标准？
>
> A：**Linux 文件系统层次结构标准 (*Filesystem Hierarchy Standard*，FHS)**上明确说明，`/mnt`用于临时挂载（例如通过 `mount` 命令手动挂载）；`/media` 适合挂载可移动存储设备（如U盘、光盘、SD卡、可移动硬盘）。
>
> 如果是内置在主机里的硬盘，最好不要碰这两个地方，系统根目录开个文件夹，再改 `/etc/fstab` 将硬盘挂在到那个文件夹上；但你要非得在这俩二选一，那就选 `/media`。
>
> FHS的原话我就不搬上去了，太长；但标题足以说明一切。
>
> - 3.11 的标题是：**`/media` : *Mount point for removable media***（`/media`：可移除介质的挂载点）；
> - 3.12 的标题是：**`/mnt` : *Mount point for a temporarily mounted filesystem***（`/mnt`：用于临时挂载文件系统的挂载点）。
>
> （参考：[FHS 3.0](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html)）
>
> 但至于如何手动或自动挂载？抱歉，这篇文章篇幅有限，没有它的位置。我会在另一篇文章里详细说明这个问题。

那么来到文件夹里面，又是什么情况呢？

## 字符设备

能够接受和发送字符的设备，就叫做“字符设备”。

在UNIX-like中，**数据流就是字节流**，而字符流是人类将字节流通过特定编码转换而来的。因此，任何能够接受或发送流式数据的设备，都叫做“字符设备”（感觉叫**“字节设备”**更合适吧？）。这包括网卡、虚拟终端、键盘鼠标，等等。

我们就以这个鼠标为例吧。现在的鼠标走的都是USB，所以想看自己鼠标分配到的`BUS`（总线）与`Device`（设备编号），只需`lsusb`就好：

```sh
$ lsusb 
...
Bus 001 Device 002: ID 1532:0060 Razer USA, Ltd RZ01-0213 Gaming Mouse [Lancehead Tournament Edition]
...
```

我这个“雷蛇”鼠标，分配到的是`Bus 001 Device 002`，设备ID是 `1532:0060`。那么我如何从这里截取数据？找USB？

HID（*Linux Human Interface Device*）可能会第一个不答应，然后把我指路到统一的`endev`（输入子系统）：

```sh
$ ls /dev/input/
by-id/   event0   event10  event12  event14  event16  event2   event4   event6   event8   mice     mouse1   
by-path/ event1   event11  event13  event15  event17  event3   event5   event7   event9   mouse0   mouse2
```

哈！原来全在这呢！我还以为要钻到南桥的USB控制器去，在那里截取USB数据流呢！......好吧，其实这样做不仅很愚蠢，也很危险。统一管起来对开发者方便，对用户也更加负责。

“你看着这`eventX`每天都不重样，但如果你只是想监听鼠标的话，只需要盯着`mice`就好啦。”

那么我们来捕获鼠标事件吧！我直接一个`sudo cat /dev/input/mice`。结果？

```sh
$ sudo cat /dev/input/mice 
▒�(�(�▒�(�8��8��▒�8��▒�8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��8��▒�8��
```

不仅乱码扎堆，光标乱跑，还跟着我鼠标指针刷屏！我移动的快，它走的就快；当我停下鼠标的时候，它也停下了。吓得我立马`^C`（）

这其实是因为，你接收到的就是最纯粹的“字节码”，而这个字节码如果通过`cat`打上终端，终端就会根据既定的编码规则（例如`UTF-8`）编码成字符。问题在于，这些字节码在`UTF-8`上是没有映射到字符的！于是你才看到了一系列的乱码。

当然，**`/dev/input/mice`现在也不推荐使用了，更好的方法是使用`eventX`**。怎么看？安装 `evtest` 就好啦。这个包不预装在电脑里，但安装也相当简单，不用自行编译，`apt install` 就OK。

```sh
$ sudo evtest
No device specified, trying to scan all of /dev/input/event*
Available devices:
/dev/input/event0:      Power Button
/dev/input/event1:      Lid Switch
/dev/input/event10:     Razer Razer Lancehead Tournament Edition
/dev/input/event11:     Acer Wireless Radio Control
/dev/input/event12:     Acer WMI hotkeys
/dev/input/event13:     HDA NVidia HDMI/DP,pcm=3
/dev/input/event14:     HDA NVidia HDMI/DP,pcm=7
/dev/input/event15:     HDA NVidia HDMI/DP,pcm=8
/dev/input/event16:     HDA NVidia HDMI/DP,pcm=9
/dev/input/event17:     sof-hda-dsp Headphone
/dev/input/event2:      Power Button
/dev/input/event3:      AT Translated Set 2 keyboard
/dev/input/event4:      Video Bus
/dev/input/event5:      PIXA3848:00 093A:3848 Mouse
/dev/input/event6:      PIXA3848:00 093A:3848 Touchpad
/dev/input/event7:      Razer Razer Lancehead Tournament Edition
/dev/input/event8:      Razer Razer Lancehead Tournament Edition Keyboard
/dev/input/event9:      Razer Razer Lancehead Tournament Edition
Select the device event number [0-17]: 

```

这里就列举了所有 `eventX` 对应的设备，例如 `event0` 是电源键，`event1` 是笔记本盖子......而我们的鼠标似乎分配到了7、8、9和10。先用7试一下吧。

```
Select the device event number [0-17]: 7
Input driver version is 1.0.1
Input device ID: bus 0x3 vendor 0x1532 product 0x60 version 0x111
Input device name: "Razer Razer Lancehead Tournament Edition"
Supported events:
  Event type 0 (EV_SYN)
  Event type 1 (EV_KEY)
    Event code 272 (BTN_LEFT)
    Event code 273 (BTN_RIGHT)
    Event code 274 (BTN_MIDDLE)
    Event code 275 (BTN_SIDE)
    Event code 276 (BTN_EXTRA)
  Event type 2 (EV_REL)
    Event code 0 (REL_X)
    Event code 1 (REL_Y)
    Event code 8 (REL_WHEEL)
    Event code 11 (REL_WHEEL_HI_RES)
  Event type 4 (EV_MSC)
    Event code 4 (MSC_SCAN)
Properties:
Testing ... (interrupt to exit)
Event: time 1758775551.430044, type 2 (EV_REL), code 0 (REL_X), value 1
Event: time 1758775551.430044, -------------- SYN_REPORT ------------
Event: time 1758775551.473993, type 2 (EV_REL), code 1 (REL_Y), value -1
Event: time 1758775551.473993, -------------- SYN_REPORT ------------
Event: time 1758775551.520049, type 2 (EV_REL), code 0 (REL_X), value 1
Event: time 1758775551.520049, type 2 (EV_REL), code 1 (REL_Y), value -1
Event: time 1758775551.520049, -------------- SYN_REPORT ------------

```

最上面的是事件类型与编号，例如`Event type 1 (EV_KEY)`就是按键事件，`Event type 2 (EV_REL)`则是相对坐标变化事件。看来没错了，这就是监听鼠标事件的地方。

Testing的时候，我稍微移动了一下鼠标，这里就收到了一系列的`Event`。例如：

```
Event: time 1758775551.430044, type 2 (EV_REL), code 0 (REL_X), value 1
```

就是说在 `1758775551.430044`（即`Thu Sep 25 2025 12:45:51 GMT+0800`）时，触发了一个事件，包含`type 2` `code 1` 和 `value` 三个信息（翻译过来就是，我这个鼠标在这个时间点上发生了`X+1`的相对位移）。

这个数据是随着下一个 `SYN_REPORT` 报告的。也就是说，鼠标是先在自己这里记录事件，等到内核向鼠标发送请求时，将记录到的事件报告给它。这一般叫做**“轮询”**，或者**“回报”**。我们能看到，这个鼠标两次回报的时间间隔一个是`0.043949`，另一个则是`0.046056`，差不多是20Hz出头的回报率。

再快速地移动呢？

```
Event: time 1758776507.528677, type 2 (EV_REL), code 1 (REL_Y), value -1
Event: time 1758776507.528677, -------------- SYN_REPORT ------------
Event: time 1758776507.530671, type 2 (EV_REL), code 0 (REL_X), value -2
Event: time 1758776507.530671, -------------- SYN_REPORT ------------
Event: time 1758776507.532670, type 2 (EV_REL), code 0 (REL_X), value -3
Event: time 1758776507.532670, -------------- SYN_REPORT ------------
```

立刻降到了每 `0.001994` 回报一次。500Hz的回报率！

雷蛇给Windows做了驱动，但Linux上还没有官方版本。不过，我这个鼠标的回报率最高可以上到1kHz。这可以在 `/sys/module/usbhid/parameters` 里改一下——但我就不尝试了。纯办公不电竞，500Hz用起来也是相当舒服的。

所以实验目的达成：我们成功捕获到来自鼠标的实时状态数据，且它的本质就是一系列的字节。如果你也跟着做了，且同样实验成功了，那就给自己来点掌声！👏👏👏

## 结语

虽然内部机理仍然相当复杂，不过从“块设备”和“字符设备”作为切入口，我们还是一窥硬件在程序员和内核眼中的样貌，以及UNIX-like“一切皆文件”的哲学。

当然，在安全和隐私要求下，我们这种做法仍然是不太安全的——真正安全的操作是，借助操作系统与桌面环境暴露的接口（API）作“白手套”，且仅在必要情况下才请求管理员权限。这部分留到下一个文章再介绍吧。

