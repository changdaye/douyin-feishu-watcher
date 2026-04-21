# Douyin Feishu Watcher

一个用于**订阅抖音博主更新**并把**新视频推送到飞书机器人**的小型服务。

当前方案特点：
- 纯 HTTP + 登录 Cookie 抓取抖音 Web API
- 不依赖 Playwright / Chromium
- 适合低配云服务器
- 支持 SQLite 去重与基线初始化
- 支持 systemd 常驻运行
- 支持打包成离线发布包后上传服务器安装

---

## 功能概览

- 轮询少量抖音博主主页
- 使用 `douyin_cookie` 调用抖音作品列表 API
- 解析最新视频信息
- 通过 SQLite 做去重和基线管理
- 将新视频推送到飞书机器人
- 首次建立基线时不补发历史视频
- 连续失败达到阈值时发送告警

---

## 项目结构

```text
app/
  config.py
  db.py
  fetcher.py
  models.py
  notifier.py
  parser.py
  scheduler.py
  service.py
creators.json.example
local.runtime.json.example
main.py
deploy/
  build-release.sh
  douyin-feishu-watcher.service
  install.sh
  run-once.sh
  service-status.sh
  service-logs.sh
```

---

## 本地开发

1. 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. 安装项目

```bash
pip install -e .[dev]
```

3. 准备配置文件

```bash
cp local.runtime.json.example local.runtime.json
cp creators.json.example creators.json
```

4. 填好：
- `local.runtime.json`
- `creators.json`

5. 运行测试

```bash
pytest tests -q
```

6. 手动跑一轮

```bash
douyin-feishu-watcher run-once
```

---

## 运行配置

程序优先读取本地 JSON 配置文件，例如：
- `local.runtime.json`
- `runtime.local.json`
- `config.local.json`

如果这些文件不存在，才回退读取 `.env`。

推荐的 `local.runtime.json`：

```json
{
  "feishu_webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/replace-me",
  "feishu_bot_secret": "",
  "douyin_cookie": "",
  "creators_file": "creators.json",
  "sqlite_path": "data/app.db",
  "poll_interval_minutes": 30,
  "request_timeout_seconds": 15,
  "failure_alert_threshold": 3
}
```

字段说明：
- `feishu_webhook_url`：飞书机器人 webhook
- `feishu_bot_secret`：飞书机器人签名密钥（如果启用加签）
- `douyin_cookie`：抖音网页登录 Cookie
- `creators_file`：博主订阅列表文件路径
- `sqlite_path`：SQLite 数据库路径
- `poll_interval_minutes`：轮询间隔（分钟）
- `request_timeout_seconds`：请求超时秒数
- `failure_alert_threshold`：连续失败多少次后发告警

---

## 博主订阅配置

`creators.json` 示例：

```json
[
  {
    "name": "示例博主",
    "profile_url": "https://www.douyin.com/user/replace-me",
    "enabled": true
  }
]
```

说明：
- `name`：显示名称，推送到飞书时会用它
- `profile_url`：抖音博主主页链接
- `enabled`：是否启用监控

---

## 离线发布包

如果服务器配置低、网络不稳定，推荐直接用**离线发布包**部署，而不是 SSH 上慢慢装环境。

### 1. 构建离线包

在 Linux 环境里执行：

```bash
bash deploy/build-release.sh
```

会生成：

```text
dist/douyin-feishu-watcher-linux-x86_64.tar.gz
```

### 2. GitHub Actions 自动打包

仓库里已经有：

```text
.github/workflows/release-bundle.yml
```

你可以：
- 手动在 GitHub Actions 里触发
- 或者打 `v*` 标签自动出包

---

## 服务器部署

### 方式一：从源码部署

```bash
bash deploy/install.sh
```

### 方式二：从离线包部署

```bash
tar -xzf douyin-feishu-watcher-linux-x86_64.tar.gz
cd douyin-feishu-watcher-linux-x86_64
cp local.runtime.json.example local.runtime.json
cp creators.json.example creators.json
# 填写配置
bash install-service.sh
```

---

## Release 包里的常用脚本

发布包解压后，顶层会有这些脚本：

### 安装并注册 systemd
```bash
bash install-service.sh
```

### 手动跑一轮检查
```bash
bash run-once.sh
```

### 查看服务状态
```bash
bash service-status.sh
```

### 查看实时日志
```bash
bash service-logs.sh
```

---

## 运行逻辑说明

- 首次运行：建立基线，不推送历史视频
- 后续运行：只推送数据库里未出现过的新视频
- 最新视频判定：按发布时间排序，不受置顶视频干扰

---

## 故障排查

### 1. 抖音抓不到数据
优先检查：
- `douyin_cookie` 是否过期
- `local.runtime.json` 是否正确

### 2. 飞书收不到消息
检查：
- `feishu_webhook_url`
- `feishu_bot_secret`
- 服务日志

### 3. 查看服务日志
```bash
journalctl -u douyin-feishu-watcher -f
```

### 4. 查看数据库基线
```bash
sqlite3 data/app.db "select creator_name, count(*) from videos group by creator_name order by creator_name;"
```

---

## 当前适用场景

适合：
- 少量博主订阅
- 小型低配云服务器
- 小团队或个人使用
- 追求稳定和低维护成本

不适合：
- 大规模高并发抓取
- 无 Cookie 的公开大规模采集
- 需要复杂后台管理系统的场景
