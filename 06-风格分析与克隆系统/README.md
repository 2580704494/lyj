# 06 风格分析与克隆系统（SC-IMG）

从参考图提取有证据的风格关系，保存为独立风格档案；更换主题时重建任务，按条件应用同一组风格规则，输出四种可复用提示词。核心系统版本 `1.0.0`，档案结构版本 `1.0`，仓库联动协议版本 `1.0`。

**先读：[逐步操作指南](./逐步操作指南.md)**。需要找提示词：真实风格须先提供参考图或完整档案；[examples](./examples/) 中仅有明确标注的自拟测试样例。

## 三种入口

| 使用场景 | 操作 |
|---|---|
| 网页大模型 | 下载并上传 [WEB_START.txt](./WEB_START.txt)，发送“启动风格分析和克隆系统”，再上传参考图 |
| 从仓库启动 | 让模型读取 [仓库根目录 START_HERE.txt](../START_HERE.txt)；本模块独立入口是 [START_HERE.txt](./START_HERE.txt) |
| 记忆调用 | 保存 [MEMORY_CARD.txt](./MEMORY_CARD.txt) 的入口信息；调用时补载完整规范和指定版本风格档案 |

启动后可直接说：

> 分析我提供的参考图，分离稳定风格和偶然主题。先给证据与不确定项，再生成通用风格档案及四版提示词。把主题更换为［新主题］时，保持风格核心，重新判断条件规则；有冲突就明确指出。

## 每次交付什么

| 交付物 | 用途 |
|---|---|
| `bundle.json` | 完整主档案，含证据、风格规则、版本、当前任务；后续复用的依据 |
| `01_prompt_zh.json` | 英文机器键名、中文描述值 |
| `02_prompt_en.json` | 与中文 JSON 同结构同 ID、英文描述值 |
| `03_prompt_zh_simple.txt` | 中文易读提示词，保留全部生效约束 |
| `04_prompt_en_natural.txt` | 英文自然语言提示词，保留全部生效约束 |
| `coverage.json` | 四版规则覆盖、条件裁剪、源档案摘要 |
| 成图与 `review.json` | 实际生成后逐项核验；没有成图不得写通过 |

四版是同一份档案的不同表达。`template` 为通用模板，保留占位符和条件；`instance` 为特定主题版本。换主题修改 `task`，不要通过删改风格核心迁就新主题；核心确需改变则派生新版本。

## 与仓库其他模块联动

[仓库联动协议](./仓库联动协议.md) 定义模块选择、输入输出、字段交接、冲突处理和回退。信息图的数值、单位、坐标尺度、图符个数、真实归属和阅读路径先锁定，再做风格化。纯插画不强制经过统计或 ISOTYPE。

联动包括双向导航、统一启动、可检查的交接文件，以及把上游约束写入 `task.requirements` 的 [离线适配工具](./tools/repo_adapter.py)。原有章节是知识与方法文档，需模型或人执行判断；适配工具不自动理解这些文档。

## 可选本地运行

Python 3.10+，仅标准库，无 API 密钥。以下命令在本模块目录执行：

```text
python tools/scimg.py check examples/demo_bundle.json
python tools/scimg.py compile examples/demo_bundle.json --out work/demo_exports --draft
python tools/repo_adapter.py examples/repo_handoff.json examples/demo_bundle.json --out work/linked
python tools/scimg.py compile work/linked/bundle.json --out work/linked_exports --draft
python -m unittest discover -s tests -v
python tools/scimg.py verify-package .
```

`work` 输出目录须新建或为空；已有文件不会被覆盖。示例是自拟测试数据，必须保留 `--draft`；真实任务检查无阻断后才能导出 ready。完整步骤见 [联动示例](./联动示例.md)，历史软件测试见 [TEST_REPORT.txt](./TEST_REPORT.txt)，本次仓库验收见 [仓库验收报告](./仓库验收报告.md)。

可复用性依靠证据、条件和检查维持。实际模型、题材和参考资料会影响结果；未做真实成图验证的档案不能宣称完美克隆或无限跨主题通用。

[仓库首页](../README.md) · [详细规范](./system/CORE.txt) · [操作协议](./system/OPERATIONS.txt) · [档案结构](./schemas/bundle.schema.json)

## 已归档风格案例

- [STYLE-CASE-001 夜城花园](./案例/STYLE-CASE-001-夜城花园/分析.md)：十三维分析、九条风格规则、通用与实例四版提示词、第一版克隆图及偏差审计。当前为 provisional，首轮纹理规则未通过，尚未验证跨主题迁移。

