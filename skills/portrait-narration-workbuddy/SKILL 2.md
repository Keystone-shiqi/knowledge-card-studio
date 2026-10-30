---
name: portrait-narration-workbuddy
description: 调用已部署的本地知识卡片与竖版口播工作流，将文案生成上传原声或MOSS本人配音、圆形头像、多风格视频、个性化页眉及自动封面；适用于WorkBuddy本地任务。
---

# 竖版口播 WorkBuddy 入口

这是入口技能，实际程序在用户选择的任务工作目录中。先检查当前目录是否包含package.json、scripts/workflow.py与SKILL.md；若没有，仅检查当前目录下portrait-narration-video或portrait-video-workflow子目录。仍找不到时，让用户选择已经解压的程序目录作为工作目录，不猜旧电脑路径、不另装第二份程序、不扫描整个硬盘。

找到程序根目录后读取其SKILL.md，并以它为本次工作流执行说明。首次安装读安装与迁移.md，由scripts/portable.py完成本机环境和配置；不要运行旧版setup_local.py，不安装IndexTTS、MuseTalk或云端配音。

日常使用.runtime/runtime.json中的Python，在工程目录运行scripts/workflow.py。配音明确MOSS-TTS-Nano，保留终审文案，默认静态圆形头像；具体模式、品牌、声音档案以本机profiles/personal.json为准。无法读取配置时先配置，不编造声音ID。

交付实际生成的MP4、自动封面及必要检查结论。配音与渲染在本机，WorkBuddy对话模型按其账号设置使用；不要把“本地配音”解释成整个Agent完全离线。失败时保留日志，不自动换音色、调用云端或消耗人物模型积分。

1.1支持八个卡片预设；风格和页眉以实际程序references/风格与页眉.md为准。只改画面时使用restyle复用原配音与时间轴，不重新合成。


首次进入任务先检查profiles/appearance.json的initialized。不存在时先运行scripts/portable.py init，自动打开八种风格选择页；必须等用户选择并保存，不能替用户默认选择或先配音。完成后继续配置声音和头像。日常沿用已选风格；想换默认时重新初始化。默认去掉FIG与幕编号。


## 1.1.2 自动下载配音软件

首次配置菜单1（安装运行环境）会先检测VoiceStudio：已安装或已有兼容后端则复用；未安装时按Windows x64/Mac M系列匹配官方v0.5.7安装包，下载并校验官方SHA256后打开安装包。菜单7或`<Python> scripts/portable.py voicestudio`也可单独触发。安装包保存在.runtime/installers/voicestudio。

系统安装界面仍由用户完成；MOSS模型、本机运行时和声音档案由VoiceStudio管理，本脚本不自动接受许可、不绕过系统提示，也不把软件安装包下载完成说成声音已经就绪。网络失败保留download-state.json，不切换第三方镜像。


1.1.3支持上传整段录音直接驱动，不需VoiceStudio。初始化先让用户选择recorded或clone，安装和配置加对应--audio-mode。已有录音不得重新克隆，不自动变速。先读实际程序的references/上传配音.md。


1.3增加图文笔记输出。用户说小红书图文/直接做图片时，用notes.py或workflow.py notes，只导出图片，不要求VoiceStudio、Whisper、FFmpeg或头像。先读references/图文笔记.md。初始化支持video/notes，风格共十套；新增brief-light/brief-dark。
