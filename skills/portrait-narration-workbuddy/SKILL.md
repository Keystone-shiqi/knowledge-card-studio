---
name: portrait-narration-workbuddy
description: 调用本地知识卡片工作流，将文字生成多风格小红书图文，或用上传原声、本地本人克隆制作竖版口播视频与封面。
---

# WorkBuddy入口

实际程序在用户选择的任务工作目录。先检查package.json、scripts/workflow.py和SKILL.md；没有时仅检查portrait-narration-video或portrait-video-workflow子目录。仍无程序时请用户选择解压后的程序根目录，不猜旧电脑路径、不扫描硬盘或安装第二份。

找到后读取程序SKILL.md及安装与迁移.md，使用portable.py，不运行旧setup_local.py。首次检查profiles/appearance.json；没有initialized时运行portable.py init，等用户选择输出形式和风格保存，不替用户选。图文六种精选，视频十种；品牌与栏目可修改，默认无FIG。

图文：读references/图文笔记.md与图文参考检索.md，由Agent把文字编排为pages，再用notes.py或workflow.py notes导出PNG/JPG。无需声音档案、头像、VoiceStudio、Whisper或FFmpeg。搜索参考时记录可见赞藏与来源，无法访问就标设计参考，不冒称已核验爆款。

视频：使用.runtime/runtime.json的Python；保留终审文案。上传原声走recorded，无需VoiceStudio且不得重新克隆或自动变速；先读references/上传配音.md。文字克隆走clone，只在此路线检测并可下载官方VoiceStudio v0.5.7，系统安装和MOSS模型/本人档案需首次完成，不接受许可或猜声音ID。本机profiles/personal.json的声音、头像和路径优先保留，不把旧配置复制到其他电脑。默认静态圆形头像，还可选本地简化嘴型、口播视频、姿势图切换；不默认用付费人物模型或IndexTTS。

仅换视觉使用restyle复用声音字幕。交付真实图片或MP4与封面、检查结果；失败保留日志，不自动改云端或消耗人物模型积分。WorkBuddy对话模型按账号设置运行，本地配音不代表整个Agent离线。不要自动发布用户内容。
