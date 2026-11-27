SC-IMG｜风格分析与克隆系统 1.0.0

先用起来

场景1：网页大模型
上传WEB_START.txt，然后发送：“启动风格分析和克隆系统。”
再上传参考图，可说：“提取这组图的风格，先输出通用四版提示词。”
若已知主题：“提取参考风格，将主题改为[主题]，保持风格核心，输出四版提示词。”
不需要运行代码或上传整个ZIP。模型必须能读取文本；分析图片还需要该入口支持视觉。上传文件本身不代表系统已自动启动。

场景2：从仓库读取
把完整目录放入自己的仓库，给能访问仓库的大模型说：
“读取仓库根目录START_HERE.txt，启动风格分析和克隆系统。”
系统会读取规范与schema。有现成bundle时同时提供其位置。
本包的仓库部署位置：https://github.com/2580704494/lyj/tree/main/06-风格分析与克隆系统
统一入口在仓库根目录 START_HERE.txt；逐步说明和模块连接见本目录 README.md、逐步操作指南.md、仓库联动协议.md。

场景3：记忆后调用
在宿主允许的情况下保存MEMORY_CARD.txt中的唤起信息，并填写完整规范与风格档案的可访问位置。
以后说：“启动风格分析和克隆系统，调用[style_id@version]，主题改为[...]。”
如果完整规范和档案仍可访问，直接恢复；只有记忆摘要则报告memory_only，补载缺失内容。不能承诺任何宿主永久、逐字记住整个系统。本包没有自动修改你的账户记忆。

四种输出
01_prompt_zh.json：英文机器键名、中文描述值。
02_prompt_en.json：同结构、同ID、英文描述值。
03_prompt_zh_simple.txt：中文易读表达，保留全部生效规则。
04_prompt_en_natural.txt：英文自然语言完整表达。
四版从同一主档案和任务编译。JSON可作提示词输入，但不是任何平台的直接API请求参数。

保存与复用
完整bundle.json是主档案，保留证据、版本、规则和任务。导出的四版是视图，不能取代原始证据档案。
换主题：修改task，保留profile核心，重新适配与导出。
改风格核心：创建新profile版本/派生ID，保留parent与差异。
无主题：task.mode=template，保留命名占位符和全部条件。
有主题：mode=instance，填写内容和上下文，不能残留占位符。
一个“validated”档案只在记录过的测试范围内通过；新题材、新模型仍需验证。

可选本地工具
要求Python 3.10+，仅使用标准库，不需要API密钥、不联网、不调用生成服务。
在本模块目录运行（06-风格分析与克隆系统）：
python tools/scimg.py check examples/demo_bundle.json
python tools/scimg.py compile examples/demo_bundle.json --out work/demo --draft
python tools/scimg.py review examples/demo_bundle.json examples/demo_review.json
python tools/scimg.py verify-package .
python -m unittest discover -s tests -v

真实使用时将examples/demo_bundle.json换成你的bundle路径。去掉--draft要求输入无阻断项；ready只表示可用提示词方案，不表示成图已经通过。
compile只写入新目录或空目录，不覆盖已有导出。coverage.json记录四版规则覆盖、裁剪、版本和源数据摘要。
check检查内置schema的结构、证据引用、依赖与条件冲突；不理解图片和中英语义。
review按已填写的观察记录聚合must结果；不能证明记录真实，也不代替看图。
verify-package核对manifest列出的文件哈希；哈希只证明文件未变，不证明作者身份或结论正确。

目录说明
START_HERE.txt             仓库入口
WEB_START.txt              网页单文件（规范+操作协议+完整bundle/review schema）
MEMORY_CARD.txt            记忆唤起与恢复入口
system/                   工作规范和操作说明
schemas/                  JSON数据结构
templates/blank_bundle.json 待填写起点；无规则时不能编译成最终提示词
examples/                 自拟测试数据，均明确标为illustrative
examples/exports_*/        同一演示档案的四版导出
tools/scimg.py             校验、编译、审计记录聚合、包完整性检查
tests/                    自动化结构与行为测试
TEST_REPORT.txt           实际软件测试结果与未做测试
manifest.json             发布文件清单及SHA-256

使用边界
本系统是文档驱动的模型工作规范和可运行的本地辅助工具，不是自带视觉模型的应用。
未附实际参考图，不存在已经为你提取好的真实风格。演示数据不能作为风格复现成功的证据。
本轮软件测试验证结构、条件、四版覆盖与审计门槛；未进行网页模型服从性比较或实际图片生成的风格保真测试。
平台记忆不等于完整档案存储。相关官方说明：https://help.openai.com/en/articles/8590148-memory-in-chatgpt （2026-11-26核对）。
