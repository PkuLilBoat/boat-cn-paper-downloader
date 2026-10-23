[English](README.md) | 简体中文

# BOAT CN Paper Downloader

用于下载中文期刊论文及公开审稿附件的 Codex / Claude Skill。Python 爬虫现有两条内置期刊映射：`journal.psych.ac.cn` 上的心理学报（`xlxb`）与心理科学进展（`xlkxjz`）。

## 能力与经验积累

- 下载两本内置 Magtech 期刊的正文 PDF，以及页面中实际提供的公开审稿附件。
- 按最新一期或年份范围下载，保存结构化目录、`metadata.jsonl` 和 `.checkpoint.json`。
- Agent 每次先读取[路由索引](references/routes/README.md)，匹配到已有经验就优先复用。
- 未匹配站点或旧路由失效时，执行[站点探索流程](references/site-discovery.md)：根据失败证据持续调整方法，直到获取成功，再验证可重复性，把成功做法与探索过程保存为可复用路由。
- 首次成功记为候选；代表性样本与重复运行验证通过后，在实际测试范围内标为稳定。遇到确切的外部阻塞时，保留进度和恢复条件，条件满足后继续。

经验积累由 **Skill 指令驱动 Agent 执行**。当前 Python CLI 只接受已登记的期刊代码；其他站点可能需要 Agent 编写专用脚本或执行浏览器步骤。本次没有新增已经实测通过的外部站点。

## 安装与快速开始

需要 Python 3，建议在虚拟环境安装两个依赖：

```bash
git clone https://github.com/PkuLilBoat/boat-cn-paper-downloader.git
cd boat-cn-paper-downloader
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install requests beautifulsoup4
python3 scripts/scrape.py --journal xlxb --output /absolute/path/to/papers --latest
```

Windows 使用 `.venv\Scripts\activate` 激活，并把输出路径替换为自己的目录。Skill 放置方式见[安装说明](references/install.md)；Agent 从 [SKILL.md](SKILL.md) 进入工作流。

## 设置与现有边界

- 内置期刊公开页面不需要 API Key；输出目录由使用者指定。
- `--from YYYY-MM --to YYYY-MM` 当前只按**年份**筛选。`--workers` 默认为 3，探索站点时使用 1。
- 断点自动读取，没有 `--resume` 参数；当前 `--delay` 参数虽被解析，但尚未应用。
- 进度与断点不能证明完整下载：完成的一期中仍可能有失败或不完整文件。需核对文件内容、论文身份与应有数量；恢复边界见[内置路由](references/routes/magtech-psych.md)。
- 审稿附件取决于期刊是否公开。网站变化、登录要求及源文件缺失可能需要继续探索或用户交互。
- 爬虫使用 Python、Requests 与 Beautiful Soup。浏览器探索依赖执行 Agent 已有的工具；项目没有内置 AI 模型、MCP 服务或任意网站通用 API。

## 隐私与仓库更新

下载文件、探索原始日志、浏览器会话和凭据保留在本地。公开路由只保存脱敏后的步骤与验证证据，不包含 Cookie、带临时令牌的下载链接或私有页面原文。后续推送 GitHub 仍需具有对应仓库授权，Skill 不会自行公开发布。

## 验证

```bash
python3 scripts/scrape.py --help
```

该命令仅检查 CLI 入口。真实下载需核对实际文件，路由文档不能代替站点在线验收。

## 许可证

仓库当前未指定许可证；依赖项目的许可证与版权要求分别保留。

## 交流与反馈

扫描二维码添加我的微信，可加入终身学习者群、交流群，一起交流学习、Obsidian、知识管理与效率工具。

![微信交流二维码](assets/wechat.jpg)

问题与建议也欢迎通过本仓库的 [GitHub Issues](https://github.com/PkuLilBoat/boat-cn-paper-downloader/issues) 提交。
