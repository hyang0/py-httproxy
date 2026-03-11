# httproxy

一个简单的多线程 HTTP 代理服务器。

## 功能特性

- 支持 HTTP 请求代理转发
- 支持 HTTPS (CONNECT 隧道)
- 多线程处理并发连接
- 支持常见的 HTTP 方法 (GET, POST, HEAD, PUT, DELETE 等)
- 自动处理 hop-by-hop 头部
- 支持 Content-Length 和 chunked 传输编码
- 可配置的连接超时和缓冲区大小
- 命令行参数支持
- 可作模块使用

## 安装

```bash
# 从源码安装
git clone https://github.com/hyang0/py-httproxy.git
cd py-httproxy
pip install -e .
```

## 使用方法

### 命令行

```bash
# 默认启动 (监听 0.0.0.0:8080)
httproxy

# 指定端口
httproxy -p 3128

# 绑定指定地址和端口
httproxy -b 127.0.0.1 -p 8888

# 开启 debug 日志
httproxy --log-level DEBUG

# 自定义超时和缓冲区大小
httproxy --timeout 60 --buffer-size 16384
```

### 命令行参数

| 参数 | 短格式 | 默认值 | 说明 |
|------|--------|--------|------|
| `--bind` | `-b` | 0.0.0.0 | 绑定地址 |
| `--port` | `-p` | 8080 | 监听端口 |
| `--log-level` | `-l` | INFO | 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL) |
| `--timeout` | | 30 | 连接超时(秒) |
| `--buffer-size` | | 8192 | 缓冲区大小(字节) |
| `--version` | `-v` | | 显示版本号 |
| `--help` | `-h` | | 显示帮助信息 |

### 作为模块使用

```python
from httproxy.server import HTTPProxyServer

# 创建并启动服务器
server = HTTPProxyServer(
    host="127.0.0.1",
    port=8888,
    timeout=60,
    buffer_size=8192
)

try:
    server.start()
except KeyboardInterrupt:
    server.stop()
```

或使用便捷函数：

```python
from httproxy.server import run_server

run_server(host="0.0.0.0", port=8080)
```

### 配置代理客户端

```bash
# 设置环境变量
export http_proxy=http://127.0.0.1:8080
export https_proxy=http://127.0.0.1:8080

# 使用 curl 测试
curl https://www.baidu.com

# 使用 Python requests
import requests
proxies = {"http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080"}
requests.get("https://www.baidu.com", proxies=proxies)
```

## 项目结构

```
py-httproxy/
├── httproxy/
│   ├── __init__.py      # 包入口
│   ├── __main__.py      # python -m httproxy 入口
│   ├── cli.py           # 命令行接口
│   └── server.py        # 核心代理服务实现
├── tests/
│   └── test_server.py   # 单元测试
├── pyproject.toml       # 项目配置
└── README.md
```

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/
```

## License

MIT
