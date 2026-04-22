# 火山云部署手册（Douyin Feishu Watcher）

本文档描述如何将 **Douyin Feishu Watcher** 部署到火山云服务器上，并验证服务是否正常运行。

---

## 一、推荐部署方式

本项目推荐使用：

- **GitHub Actions 构建 Linux 离线发布包**
- 将离线包上传到火山云服务器
- 配置 `local.runtime.json` 和 `creators.json`
- 执行安装脚本完成部署

这样做的原因：

- 火山云低配机器不适合长时间在线安装依赖
- SSH 会话可能不稳定
- 离线包方式更稳定、步骤更少、可重复性更高

---

## 二、服务器要求

建议最低配置：

- 2 核 CPU
- 2G 内存
- 40G 磁盘
- Linux x86_64
- 可访问 GitHub / 飞书 / 抖音

如果机器较小，建议开启 swap。

---

## 三、需要准备的文件

部署时需要以下文件：

1. `douyin-feishu-watcher-linux-x86_64.tar.gz`
2. `local.runtime.json`
3. `creators.json`

其中：

- `tar.gz` 是 GitHub Actions 生成的离线发布包
- `local.runtime.json` 是运行配置
- `creators.json` 是订阅博主列表

---

## 四、local.runtime.json 示例

```json
{
  "feishu_webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/你的webhook",
  "feishu_bot_secret": "你的飞书签名",
  "douyin_cookie": "你的整串抖音cookie",
  "creators_file": "creators.json",
  "sqlite_path": "data/app.db",
  "poll_interval_minutes": 30,
  "request_timeout_seconds": 15,
  "failure_alert_threshold": 3,
  "heartbeat_enabled": true,
  "heartbeat_interval_hours": 6,
  "startup_notification_enabled": true
}
```

### 字段说明

- `feishu_webhook_url`：飞书机器人 webhook
- `feishu_bot_secret`：飞书机器人签名密钥
- `douyin_cookie`：抖音网页登录 Cookie
- `creators_file`：博主列表文件路径
- `sqlite_path`：SQLite 数据库路径
- `poll_interval_minutes`：轮询间隔（分钟）
- `request_timeout_seconds`：HTTP 请求超时（秒）
- `failure_alert_threshold`：连续失败多少次后发告警
- `heartbeat_enabled`：是否发送健康心跳
- `heartbeat_interval_hours`：心跳间隔小时数
- `startup_notification_enabled`：服务启动成功后是否发通知

---

## 五、creators.json 示例

```json
[
  {
    "name": "口罩哥研报60秒",
    "profile_url": "https://www.douyin.com/user/xxxxx",
    "enabled": true
  },
  {
    "name": "刘德超",
    "profile_url": "https://www.douyin.com/user/yyyyy",
    "enabled": true
  }
]
```

### 字段说明

- `name`：推送时显示的博主名称
- `profile_url`：抖音博主主页链接
- `enabled`：是否启用监控

---

## 六、上传文件到火山云

假设本地 SSH 别名是 `huoshan`：

```bash
scp douyin-feishu-watcher-linux-x86_64.tar.gz huoshan:/root/
scp local.runtime.json huoshan:/root/
scp creators.json huoshan:/root/
```

如果 SSH 不稳定，也可以通过火山云控制台的文件上传功能手动上传。

---

## 七、部署步骤

登录服务器：

```bash
ssh huoshan
```

执行：

```bash
rm -rf /opt/douyin-feishu-watcher-linux-x86_64 /opt/douyin-feishu-watcher
mkdir -p /opt

tar -xzf /root/douyin-feishu-watcher-linux-x86_64.tar.gz -C /opt
mv /opt/douyin-feishu-watcher-linux-x86_64 /opt/douyin-feishu-watcher

cp /root/local.runtime.json /opt/douyin-feishu-watcher/local.runtime.json
cp /root/creators.json /opt/douyin-feishu-watcher/creators.json

cd /opt/douyin-feishu-watcher
bash install-service.sh
```

---

## 八、部署完成后验证

### 1. 查看服务状态

```bash
systemctl status douyin-feishu-watcher
```

### 2. 查看实时日志

```bash
journalctl -u douyin-feishu-watcher -f
```

### 3. 手动跑一轮

```bash
/opt/douyin-feishu-watcher/.venv/bin/douyin-feishu-watcher run-once
```

### 4. 查看数据库基线

```bash
sqlite3 /opt/douyin-feishu-watcher/data/app.db "select creator_name, count(*) from videos group by creator_name order by creator_name;"
```

---

## 九、你应该收到的飞书消息

正常运行后，飞书会收到三类消息：

### 1. 启动成功通知
服务启动成功后发送一条

### 2. 新视频通知
当监控的博主出现新视频时发送

### 3. 健康心跳
默认每 6 小时发送一条

---

## 十、常用运维命令

### 重启服务

```bash
systemctl restart douyin-feishu-watcher
```

### 停止服务

```bash
systemctl stop douyin-feishu-watcher
```

### 开机自启

```bash
systemctl enable douyin-feishu-watcher
```

### 关闭开机自启

```bash
systemctl disable douyin-feishu-watcher
```

---

## 十一、常见问题

### 1. 没有新视频推送
先执行：

```bash
/opt/douyin-feishu-watcher/.venv/bin/douyin-feishu-watcher run-once
```

如果输出类似：

```text
checked=5 new_videos=0 failed=none
```

说明服务本身正常，只是当前没有新的未记录视频。

---

### 2. 飞书没有收到消息
查看：

```bash
journalctl -u douyin-feishu-watcher -n 100 --no-pager
```

检查：
- webhook 是否正确
- 签名是否正确
- 网络是否超时

---

### 3. 抖音抓取失败
重点检查：
- `local.runtime.json` 里的 `douyin_cookie`

Cookie 过期后，需要重新替换。替换后重启服务：

```bash
systemctl restart douyin-feishu-watcher
```

---

### 4. 服务起不来
查看状态：

```bash
systemctl status douyin-feishu-watcher
```

查看日志：

```bash
journalctl -u douyin-feishu-watcher -n 200 --no-pager
```

---

### 5. SSH 经常断开
火山云低配机器上，这更像是系统资源或 sshd 稳定性问题，不一定是本项目本身造成的。

建议：
- 尽量使用离线包部署
- 减少长时间 SSH 会话
- 必要时通过火山云网页控制台执行命令
- 查看 `journalctl -u sshd`

---

## 十二、更新部署

如果项目发布了新版本：

1. 下载新的 `douyin-feishu-watcher-linux-x86_64.tar.gz`
2. 保留原有 `local.runtime.json` 和 `creators.json`
3. 按部署步骤重新覆盖安装
4. 再执行：

```bash
bash install-service.sh
```

---

## 十三、推荐排查顺序

如果你怀疑服务不正常，推荐按这个顺序检查：

1. `systemctl status douyin-feishu-watcher`
2. `journalctl -u douyin-feishu-watcher -n 100 --no-pager`
3. `/opt/douyin-feishu-watcher/.venv/bin/douyin-feishu-watcher run-once`
4. `sqlite3 /opt/douyin-feishu-watcher/data/app.db ...`
5. 检查 `local.runtime.json` 的 Cookie / 飞书配置

---

## 十四、总结

本项目在火山云上的推荐方式是：

> **离线包部署 + JSON 本地配置 + systemd 常驻运行**

这是目前最稳、最适合低配云机器的方案。
