# p2p — 三环并行渗透测试 pi 插件

把一套「并行 + 持久化 + 门控 + 经验沉淀」的授权渗透测试架构，以**单个 pi agent 扩展**的形式套在 [pi coding agent](https://github.com/earendil-works/pi) 上。不调提示词，重构架构。

> ⚠️ 仅用于**已授权**的安全测试（SRC 项目 / 靶场 / 自有资产）。scope 门控默认硬拦截越界目标。

## 架构

```
                ┌──────────────────────────────┐
                │  graphd : Kuzu 共享状态层      │
                │  Engagement/Endpoint/Signal_/ │
                │  Hypothesis/Finding/          │
                │  ExperienceWeight/AgentIdentity│
                └───────┬─────────┬────────┬────┘
              写信号    │         │读信号写Finding   │读写假设
        ┌───────────────▼┐  ┌─────▼────────┐  ┌▼──────────┐
        │ ① 广度发现环     │  │ ③ 深度攻击环  │  │ ② 创造探索环│
        │ n 个 pi 实例并发 │  │ 常驻消费信号  │  │ 反思唤醒时 │
        │ 每实例一条业务链 │  │ 三层递进验证  │  │ 反转假设   │
        └────────────────┘  └──────────────┘  └───────────┘
                          ┌──────────────────┐
                          │ 仲裁层(插件内钩子) │
                          │ scope门控·铁律拦截·│
                          │ 停滞检测·反思唤醒  │
                          └──────────────────┘
```

- **发现环**：n 个 pi 子进程（`pi --mode json -p --no-session`）并发覆盖模块，走完整业务链路做缝隙检测与轻量验证，输出候选攻击面/已排除方向/待深入信号
- **深度攻击环**：信号驱动三层递进——L1 广撒网 → L2 异常/行为/时序特征剪枝 → L3 跨端点组合攻击链；权重闸门决定算力去向
- **创造探索环**：连续无发现时反转假设（有WAF↔无WAF）、架构重验证、清空记忆独立重构
- **仲裁层**：`tool_call` 钩子在 bash 执行前做 scope 白名单校验与危险命令铁律拦截；看门狗检测三环停滞并提示唤醒
- **持久化**：所有状态写 Kuzu 图（单写者 sidecar 规避多进程锁）；AgentIdentity 持续记录 checkpoint，worker 可从断点恢复
- **免工具核心**：只需 `bash + python + curl`；agent 自写探针，证据链更干净、更抗 WAF

## 安装

```bash
# 依赖: Node >= 22, Python 3.12+, kuzu (pip install kuzu)
tar xzf p2p-v*.tar.gz -C ~/p2p && cd ~/p2p
npm install --prefix pi @earendil-works/pi-coding-agent@latest
(cd home/.pi/agent/extensions/pentest && npm install)   # MCP SDK(可选)
pip install kuzu                                        # graphd 依赖
# 把你的 pi 凭证放入 home/.pi/agent/auth.json (或启动后登录)
```

## 启动

```bash
source env.sh          # PATH/HOME 全部切到 p2p 内, 与本机已有 pi 完全隔离
python3 graphd/app.py & # 图数据库 sidecar (:8765)
p2p                     # 进入隔离的 pi
```

## 使用

| 命令 | 说明 |
|---|---|
| `/pentest <target> [scope] [n]` | 建立 engagement 并启动发现环 n 实例 |
| `/pentest-status` | 三环状态总览 |
| `/pentest-deep` | 手动触发深度环消费高权重信号 |
| `/pentest-creative [focus]` | 手动触发创造探索环 |
| `/pentest-stop` | 停止全部 worker 并冻结 |

工具：`p2p_status`（只读状态）、`p2p_graph`（只读 Cypher 查询）

### MCP 扩展位（`home/.pi/agent/pentest-mcp.json`）

- `chrome`：Google chrome-devtools-mcp（CDP 操控浏览器，覆盖 SPA/前端交互），默认启用
- `burp`：PortSwigger Burp MCP server 接口已预留，装好后改路径并把 `enabled` 改为 `true`

## 目录

```
home/.pi/agent/extensions/pentest/   ★ pi 插件本体 (TS)
graphd/app.py                        Kuzu 单写者 HTTP sidecar
home/.pi/agent/skills/pentest/       9区边界 SKILL.md
bin/                                 可选加速工具位(默认空)
env.sh                               隔离环境切换脚本
```

## 设计文档

边界文件遵循《AI 辅助漏洞挖掘系统设计指南》：垃圾洞清单置顶、灵魂金句、速查卡防遗忘、七问验证门、决策树而非固定流程、只报"已证明的结果"。详见 `home/.pi/agent/skills/pentest/SKILL.md`。

## License

MIT

## 实现状态(声明即契约)

| 声明 | 状态 | 验证途径 |
|---|---|---|
| 三环并行 + 图共享状态 | ✅ 实装 | compliance_check |
| pi.on("") tool-call 拦截门控 | ✅ 实装(pi-coding-agent types L922) | deny 形状 {block,reason} |
| worker OS timeout + 组杀 | ✅ 实装(#11/#9) | 进程树验证 |
| AgentIdentity checkpoint 写入 | ✅ 实装 | rings.ts close handler |
| 结构化写端点(/write/*) | ✅ 实装(Wave1) | graphd v2 |
| 共享内核统一调度(p2p-core) | ⏳ 迁移中 | wufufu770/p2p-core |
| proxygate 出口治理 | ⏳ 已建成未接线 | p2p-core packages/tools |
| 验证器环 | ⏳ 计划中 | — |
