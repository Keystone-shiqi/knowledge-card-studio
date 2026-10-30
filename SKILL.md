---
name: portrait-narration-video
description: 将文字生成多风格小红书图文笔记，或用上传原声及本地配音生成竖版讲解视频与封面；支持静态圆形头像、校准嘴型、现有口播视频和姿势图切换。
---

# 竖版口播工作流

工程根目录为本SKILL.md所在目录。首次安装读[安装与迁移.md](安装与迁移.md)，四种人物模式及输入字段读[references/模式与配置.md](references/模式与配置.md)。本包通过Python/Node执行，使用WorkBuddy或其他能运行本地命令的Agent均可，无Codex专属工具依赖。

默认本地VoiceStudio + MOSS-TTS-Nano配音，模型参数明确指定moss-tts-nano，不跟随应用界面的默认引擎。MOSS不提供精细情绪控制，不能把文案里的情绪描述说成已经实际生效。包内不提供IndexTTS、MuseTalk或云端人物安装器。

执行任务时：

1. 读取profiles/personal.json；不存在则先按安装指南配置，不猜测声音ID或电脑路径。当前Python路径读取.runtime/runtime.json的python字段，使用该解释器运行脚本。
2. 保留终审文案，合理分幕，生成job.json；示例见examples/job.json。标题去标点、使用已嵌入的思源黑体Bold，正文与配音标点保留。未指定单条风格时沿用已选默认；1080×1920、30fps。每幕headline最多40字，cards最多3条，每条70字；封面hook/data/question各最多35字。
3. 不指定人物时使用配置里的static。导入本人素材库后可选择A西装/B卫衣/C休闲外衫；B提供三姿势图，A/C未提供姿势图。新用户自己的照片默认仅静态模式；新图嘴部位置需另行校准。
4. 在工程目录运行 `<运行时Python> -X utf8 scripts/workflow.py run --job <job.json> --profile profiles/personal.json`，按需加--avatar A/B/C或--avatar-mode。语速校准发生在配音后、字幕对齐前；处理幅度有界、保留原音频，不能声称句内情绪已解决。
5. 完成后读取任务status.json、hyperframes-check.json、ffprobe.json，检查封面和解码帧再交付jobs/中实际生成的MP4及封面。不能把环境自测的测试音冒充本人声音，不能从转写一致性推断声音相似或嘴型自然。

照片类模式先生成声音再做本地字幕对齐，音频决定分镜时长。上传视频默认保留其原音轨并按真实时间切分，不能自动换声音制造音画错位。嘴型模式只是本地近似嘴形与眨眼；姿势图是静态替换，都不能冒充完整数字人动作。

导入素材、模型安装和生成均是本地操作；首次下载依赖/权重需要联网，WorkBuddy对话模型仍按其自身账号设置工作。私人录音、头像、缓存、配置及账号信息不应混入通用程序分发包。出现错误先保留日志，不自动改用云端、其他音色或付费人物模型。


## 1.3 图文笔记入口（优先分流）

先判断用户要“视频”还是“图文/小红书笔记/直接做图片”。图文请求读取[references/图文笔记.md](references/图文笔记.md)，用notes.py或workflow.py notes导出PNG/JPG；不要走run、配音、ASR或视频渲染，不要求声音档案和头像。Agent负责把用户文字编排为pages，示例examples/notes.json；不要求用户写JSON。

风格现有10套，新增brief-light/brief-dark，对应本轮产品分析参考。所有旧样式保留。只借鉴版式，不带入参考图产品与数据；标题思源黑体Bold700、默认无FIG，正文和来源按原稿保留。无用户配图时用文字/流程版式，不生成假证据照片。


## 首次初始化与日常顺序（1.1.1）

首次先检查profiles/appearance.json。不存在或initialized不为true时，先运行 `<本机Python> -X utf8 scripts/portable.py init`，它会在本机默认浏览器打开十种风格对比图和选择页。让用户亲自选一种、保存后再继续，不能替用户选studio-paper、从demo推断偏好或先开始配音。脚本等待用户保存期间保持任务可交互；浏览器打不开时给出脚本打印的本机URL。取消或超时不视为已选择。

已保存时读取theme/header，按所选风格继续，不重复弹出。用户说“换默认风格”时重新运行init；只改一条视频可在job.theme覆盖。不指定单条风格时不要往job填固定theme，以免覆盖已选默认。run命令会在未初始化时拒绝正式生成；环境自测仍可独立运行。

菜单启动和声音configure前也会检查并自动打开初始化。初始化只保存视觉设置，不要求声音服务先启动。其后按安装指南准备MOSS声音档案与头像。默认移除FIG和幕编号，仅保留栏目文字；仍可显式定制其他前缀。修改视觉不覆盖声音、头像、路径。


## 1.1 多风格与页眉

首次必须用户选择默认风格；用户可选择paper/navy/editorial-ink/swiss-blue/swiss-yellow/swiss-green/swiss-orange。十个预设共五类视觉体系，详见[references/风格与页眉.md](references/风格与页眉.md)。用户明确选风格时优先执行，不把旧“只能浅灰黑红”当作禁止切换。归藏样式是竖版改编，标题继续思源黑体Bold700，不冒充原PPT完整模板。

单条主题写job.theme；长期默认只合并更新profile.theme/header，不覆盖配音、头像和路径。header可改品牌、右上栏目、FIG前缀、幕编号/起始值、每幕栏目；品牌栏和编号行可分别隐藏。封面自动跟随。仅改风格或页眉时优先使用restyle复用原声音和字幕，不能改口播文案或宣称重新验收了音质。所有配置在配音前校验。


## 1.1.2 自动下载配音软件

首次配置菜单1（安装运行环境）会先检测VoiceStudio：已安装或已有兼容后端则复用；未安装时按Windows x64/Mac M系列匹配官方v0.5.7安装包，下载并校验官方SHA256后打开安装包。菜单7或`<Python> scripts/portable.py voicestudio`也可单独触发。安装包保存在.runtime/installers/voicestudio。

系统安装界面仍由用户完成；MOSS模型、本机运行时和声音档案由VoiceStudio管理，本脚本不自动接受许可、不绕过系统提示，也不把软件安装包下载完成说成声音已经就绪。网络失败保留download-state.json，不切换第三方镜像。


## 1.1.3 两种音频来源

首次初始化可选择上传配音(recorded，推荐)或文字克隆(clone)。VoiceStudio仅克隆路线需要；有实际录音时优先保留原声，不要求安装VoiceStudio或再克隆。完整字段与操作见[references/上传配音.md](references/上传配音.md)。--audio或job.audio_source显式覆盖TTS；多幕按真实audio_start/audio_end完整覆盖，不能猜时间、截漏或对每幕重复整段音频。只有录音时先用transcribe_recording.py得到文字与实际时间，再编排分镜。

上传原声不自动变速，不把简化嘴型说成精准口型或手势。新用户录音模式的install/configure跳过VoiceStudio；既有MOSS配置保留，不能默认覆盖。
