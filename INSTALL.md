# 给安装Agent的说明 · v1.3.0

仓库：https://github.com/Keystone-shiqi/knowledge-card-studio 。先确认用户指定的安装目录和输出形式；不要覆盖已有私人配置。

## 获取程序

Git可用时clone该公开仓库，推荐固定v1.3.0标签；否则从GitHub Release或Code → Download ZIP下载、解压。程序根目录含SKILL.md、package.json和scripts。解压后的文件夹可改名；配置后移动目录应重新检查本机路径。不要复制其他电脑的.runtime或node_modules。

## 基础环境

本项目目标平台为Mac Apple Silicon和Windows x64。Python>=3.9（建议3.11）、Node>=22及npm需要可运行。缺失时从官方来源或本机已有包管理器安装；不假设所有Mac都有brew或所有Windows都有winget。系统权限与安装提示由用户处理，不索取密码、密钥。

## 首次初始化

读取根目录SKILL.md。运行`<Python> -X utf8 scripts/portable.py init`，打开本机默认浏览器中的选择页；等待用户选择“图文/视频”及十种风格之一并保存，不替用户预选。打不开浏览器时给出脚本打印的本机URL。选择写入profiles/appearance.json。无需先安装声音模型。

## 图文模式（轻量）

运行`<Python> scripts/portable.py install --output-mode notes`。它只安装Node依赖和浏览器；不安装Whisper/PyTorch/VoiceStudio，不要求FFmpeg。不要先跑视频环境来制作静态图片。

用`<Python> scripts/workflow.py notes --job examples/notes.json`自测。纯图文可以没有profiles/personal.json，单条任务可提供theme/header。用户发来文字后，由Agent分配pages，编排封面、对比、流程、数字、图片或结论版式，再执行notes。完整字段见references/图文笔记.md。

## 视频模式

上传原声：install --output-mode video --audio-mode recorded，然后configure --output-mode video --audio-mode recorded --photo <本人照片>。需要FFmpeg/ffprobe与Whisper字幕环境，不需要VoiceStudio。

文字克隆：install --output-mode video --audio-mode clone。安装器复用已有VoiceStudio，或下载并校验官方安装包、打开安装界面。用户完成系统安装、MOSS模型和自己的声音档案，再configure --output-mode video --audio-mode clone --photo <本人照片>选择实际档案。

已有本机配置先检查、保留，不重复克隆；未知声音ID不猜。嘴型需要图片校准，不能承诺任意照片精准同步。没有录音时不能用演示声音冒充本人。模型许可由用户确认，不自动改用云端或付费人物生成。

## 检查和交付

运行时位置读取.runtime/runtime.json。图文检查`portable.py check --output-mode notes`，随后检查真实PNG/JPG、check.json和status.json；交付图片组与发布文案，不自动发布。内容放不下就拆页，不压成看不清的小字，也不编造来源。

视频检查workflow.py doctor，上传原声路线可加--recorded；使用smoke生成的测试音不能证明声音克隆成功。按实际文案/原声生成短片后核对字幕、人物、封面和ffprobe。本人音色/语气仍需试听。

## WorkBuddy入口

上传本仓库根目录WorkBuddy入口Skill.zip，再把解压后的程序根目录选为任务工作目录；不用移进WorkBuddy的安装目录。只给GitHub URL可让能执行本地命令的Agent拉取程序并按本说明部署，但Skill长期注册方式由客户端决定。不要凭空承诺所有Agent都能通过URL自动注册。

首次部署完成后报告实际目录、版本、输出形式、已通过的检查和仍需用户完成的事项。其他电脑仍需本机安装，不能把iCloud同步等同于跨系统部署。
