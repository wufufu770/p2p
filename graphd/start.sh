#!/usr/bin/env bash
# p2p graphd 启动器: 端口/库路径钉定(勿改 app.py 默认值)
cd "$(dirname "$0")"
export P2P_GRAPH_PORT=8765
unset P2P_GRAPH   # 用脚本同目录 kuzu_db, 防跨仓串库
exec python3 app.py
