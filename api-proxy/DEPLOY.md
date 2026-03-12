# API Proxy 部署文档

## 目录

- [配置说明](#配置说明)
- [Linux 部署](#linux-部署)
- [Windows 部署](#windows-部署)
- [验证服务](#验证服务)
- [常见问题](#常见问题)

---

## 配置说明

> 在部署前，**必须修改** `proxy.py` 顶部配置区，或通过**环境变量**注入。

| 环境变量 / 代码变量       | 说明                              | 示例值                                          |
|--------------------------|-----------------------------------|------------------------------------------------|
| `TOKEN_API_URL`          | Token 接口地址（POST）             | `https://api.example.com/auth/login`           |
| `TOKEN_REQUEST_TYPE`     | 请求体格式 `json` 或 `form`        | `json`                                         |
| `TOKEN_PARAM_1_NAME`     | 第一个参数名                       | `username`                                     |
| `TOKEN_PARAM_1_VALUE`    | 第一个参数值                       | `admin`                                        |
| `TOKEN_PARAM_2_NAME`     | 第二个参数名                       | `password`                                     |
| `TOKEN_PARAM_2_VALUE`    | 第二个参数值                       | `secret123`                                    |
| `TARGET_API_URL`         | 第二个接口的**完整地址**（直接转发，不拼接路径） | `https://ai.example.com/api/chat/send` |
| `AUTH_HEADER_NAME`       | 注入 Token 的 Header 字段名        | `Auth`、`Authorization`、`X-Token` 等          |
| `LOCAL_API_PREFIX`       | 对外暴露的路径前缀，前缀下所有路径均被代理 | `/v1`（支持 `/v1/chat/completions`、`/v1/responses` 等） |
| `PROXY_HOST`             | 代理监听 IP（默认 `0.0.0.0`）      | `0.0.0.0`                                      |
| `PROXY_PORT`             | 代理监听端口（默认 `8080`）         | `8080`                                         |
| `TOKEN_REFRESH_INTERVAL` | Token 刷新间隔秒数（默认 `1800`）  | `1800`                                         |

**两种配置方式（任选一种）：**

方式 A：直接修改 `proxy.py` 第 30~60 行的默认值。

方式 B：通过环境变量覆盖（推荐生产环境）：
```bash
export TOKEN_API_URL="https://api.example.com/auth/login"
export TOKEN_PARAM_1_NAME="username"
export TOKEN_PARAM_1_VALUE="admin"
# ... 其余变量同理
```

---

## Linux 部署

### 1. 环境准备

```bash
# 安装 Python 3.9+（若未安装）
sudo apt update && sudo apt install -y python3 python3-pip python3-venv
# 或 CentOS/RHEL:
# sudo yum install -y python3 python3-pip

python3 --version   # 确认版本 >= 3.9
```

### 2. 上传文件 & 安装依赖

```bash
# 创建目录
mkdir -p /opt/api-proxy
cd /opt/api-proxy

# 将 proxy.py 上传到此目录，然后：
python3 -m venv venv
source venv/bin/activate
pip install fastapi "uvicorn[standard]" httpx
deactivate
```

### 3. 创建环境变量配置文件

```bash
cat > /opt/api-proxy/.env << 'EOF'
TOKEN_API_URL=https://api.example.com/auth/login
TOKEN_REQUEST_TYPE=json
TOKEN_PARAM_1_NAME=username
TOKEN_PARAM_1_VALUE=admin
TOKEN_PARAM_2_NAME=password
TOKEN_PARAM_2_VALUE=secret123
TARGET_API_URL=https://ai.example.com/api/chat/send
LOCAL_API_PREFIX=/v1
AUTH_HEADER_NAME=Auth
PROXY_HOST=0.0.0.0
PROXY_PORT=8080
TOKEN_REFRESH_INTERVAL=1800
EOF

chmod 600 /opt/api-proxy/.env   # 保护密码
```

### 4. 注册 systemd 服务（推荐）

```bash
sudo tee /etc/systemd/system/api-proxy.service << 'EOF'
[Unit]
Description=API Proxy Service
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=nobody
WorkingDirectory=/opt/api-proxy
EnvironmentFile=/opt/api-proxy/.env
ExecStart=/opt/api-proxy/venv/bin/python proxy.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# 安全加固（可选）
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable api-proxy   # 开机自启
sudo systemctl start  api-proxy   # 立即启动
```

### 5. 常用管理命令

```bash
sudo systemctl status  api-proxy   # 查看状态
sudo systemctl restart api-proxy   # 重启
sudo systemctl stop    api-proxy   # 停止
journalctl -u api-proxy -f         # 实时查看日志
journalctl -u api-proxy --since "1 hour ago"  # 最近1小时日志
tail -f /opt/api-proxy/proxy.log   # 查看应用日志文件
```

### 6. （可选）Nginx 反向代理

如需 80/443 端口对外提供服务：

```nginx
# /etc/nginx/sites-available/api-proxy
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass         http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;

        # SSE 流式响应必须关闭缓冲
        proxy_buffering    off;
        proxy_cache        off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;

        chunked_transfer_encoding on;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/api-proxy /etc/nginx/sites-enabled/
sudo nginx -t && sudo nginx -s reload
```

### 7. 开放防火墙端口

```bash
# UFW（Ubuntu）
sudo ufw allow 8080/tcp

# firewalld（CentOS/RHEL）
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --reload
```

---

## Windows 部署

### 1. 环境准备

从 [python.org](https://www.python.org/downloads/) 下载安装 Python 3.9+，
安装时勾选 **"Add Python to PATH"**。

```powershell
python --version   # 确认版本 >= 3.9
```

### 2. 安装依赖

```powershell
# 进入部署目录（将 proxy.py 放在此处）
cd C:\api-proxy

# 创建虚拟环境
python -m venv venv
.\venv\Scripts\Activate.ps1     # PowerShell
# 或 cmd: venv\Scripts\activate.bat

pip install fastapi "uvicorn[standard]" httpx
```

> 若 PowerShell 执行策略限制，先运行：
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 3. 创建环境变量配置

创建 `C:\api-proxy\.env`（可用记事本编辑）：

```ini
TOKEN_API_URL=https://api.example.com/auth/login
TOKEN_REQUEST_TYPE=json
TOKEN_PARAM_1_NAME=username
TOKEN_PARAM_1_VALUE=admin
TOKEN_PARAM_2_NAME=password
TOKEN_PARAM_2_VALUE=secret123
TARGET_API_URL=https://ai.example.com/api/chat/send
LOCAL_API_PREFIX=/v1
AUTH_HEADER_NAME=Auth
PROXY_HOST=0.0.0.0
PROXY_PORT=8080
TOKEN_REFRESH_INTERVAL=1800
```

创建启动脚本 `C:\api-proxy\start.bat`：

```bat
@echo off
cd /d C:\api-proxy
for /f "tokens=1,2 delims==" %%a in (.env) do set %%a=%%b
call venv\Scripts\activate.bat
python proxy.py
```

### 方式 A：手动运行（测试用）

```powershell
cd C:\api-proxy
.\start.bat
# 或直接:
.\venv\Scripts\python.exe proxy.py
```

### 方式 B：使用 NSSM 注册为 Windows 服务（推荐生产）

1. 下载 [NSSM](https://nssm.cc/download)，解压到 `C:\tools\nssm\`

2. 以**管理员**身份打开 PowerShell：

```powershell
# 安装服务
C:\tools\nssm\win64\nssm.exe install ApiProxy "C:\api-proxy\venv\Scripts\python.exe" "proxy.py"

# 设置工作目录
C:\tools\nssm\win64\nssm.exe set ApiProxy AppDirectory "C:\api-proxy"

# 设置环境变量（一行，分号分隔）
C:\tools\nssm\win64\nssm.exe set ApiProxy AppEnvironmentExtra `
  "TOKEN_API_URL=https://api.example.com/auth/login" `
  "TOKEN_PARAM_1_NAME=username" `
  "TOKEN_PARAM_1_VALUE=admin" `
  "TOKEN_PARAM_2_NAME=password" `
  "TOKEN_PARAM_2_VALUE=secret123" `
  "TARGET_API_URL=https://ai.example.com/api/chat/send" `
  "LOCAL_API_PREFIX=/v1" `
  "PROXY_PORT=8080"

# 配置日志
C:\tools\nssm\win64\nssm.exe set ApiProxy AppStdout "C:\api-proxy\service-stdout.log"
C:\tools\nssm\win64\nssm.exe set ApiProxy AppStderr "C:\api-proxy\service-stderr.log"

# 启动服务
Start-Service ApiProxy

# 设置开机自启
Set-Service ApiProxy -StartupType Automatic
```

### 方式 C：使用任务计划程序（无需第三方工具）

```powershell
# 以管理员身份运行
$action  = New-ScheduledTaskAction -Execute "C:\api-proxy\venv\Scripts\python.exe" `
             -Argument "proxy.py" -WorkingDirectory "C:\api-proxy"
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest

Register-ScheduledTask -TaskName "ApiProxy" `
  -Action $action -Trigger $trigger `
  -Settings $settings -Principal $principal
```

### Windows 常用管理命令

```powershell
# NSSM 方式
Start-Service ApiProxy
Stop-Service  ApiProxy
Restart-Service ApiProxy
Get-Service   ApiProxy

# 实时查看日志
Get-Content C:\api-proxy\proxy.log -Wait -Tail 50
```

### Windows 防火墙放行端口

```powershell
# 管理员权限执行
New-NetFirewallRule -DisplayName "API Proxy 8080" `
  -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
```

---

## 验证服务

### 健康检查

```bash
curl http://localhost:8080/_proxy/health
```

预期响应：
```json
{
  "status": "ok",
  "has_token": true,
  "token_age_seconds": 12,
  "refresh_interval_seconds": 1800,
  "target": "https://ai.example.com"
}
```

### 测试 ChatGPT 对话（普通请求）

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "hello"}]
  }'
```

### 测试流式响应

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "hello"}],
    "stream": true
  }'
```

---

## 常见问题

**Q: 启动报错 `初始 Token 获取失败`**
- 检查 `TOKEN_API_URL` 是否正确可访问
- 检查参数名/值是否和接口文档一致
- 检查 `TOKEN_REQUEST_TYPE` 是否和接口要求匹配（`json` vs `form`）

**Q: 代理转发返回 401/403**
- Token 可能已过期，检查 `TOKEN_REFRESH_INTERVAL` 是否小于接口实际过期时间
- 检查 Header 字段名是否确实为 `Auth`（区分大小写）

**Q: 流式响应卡住或无数据**
- Nginx 层必须设置 `proxy_buffering off`
- 确认目标接口真正支持 SSE 流式输出

**Q: Windows 下 venv 激活失败**
- 以管理员身份运行：`Set-ExecutionPolicy RemoteSigned -Scope LocalMachine`

**Q: 日志文件在哪里**
- 应用日志：`proxy.py` 同级目录的 `proxy.log`
- Linux systemd 日志：`journalctl -u api-proxy`
- Windows NSSM 日志：`C:\api-proxy\service-stdout.log`
