# hermes现阶段详细工作计划

## 一、任务概述

完成Epic秘书和workbuddy两个智能体在阿里云轻量主机上的部署，绑定飞书机器人，落实安全加固措施，验证全流程可正常工作。

## 二、前置信息

### 服务器信息
- 服务器：阿里云轻量主机
- 实例ID：iZwz93uizjttuzyb96khrxZ
- 公网IP：8.129.3.49
- 基础环境：已配置好Nginx、systemd、HTTPS证书
- 端口规划：框架已预留多个扩展端口，每个智能体分配一个独立端口

### 飞书信息
- Webhook URL：https://open.feishu.cn/open-apis/bot/v2/hook/d2714162-1992-47d7-a499-5bc6bb3eaf42
- 飞书官方IP段：
  103.170.108.0/23
  118.112.184.0/23
  119.123.0.0/16
  203.208.0.0/16

### SSH登陆说明
- 老袁协助SSH登陆到阿里云服务器
- 如需执行命令，由hermes提供命令，老袁在服务器上执行
- 如需上传文件，由老袁协助上传
- 部署过程中遇到问题，及时在飞书沟通

## 三、部署步骤

### 步骤1：部署Epic秘书到阿里云并绑定飞书

#### 1.1 环境准备
```bash
# 1. 登录阿里云服务器
# 2. 创建部署目录
sudo mkdir -p /opt/epic-secret
sudo chown [用户名]:[用户名] /opt/epic-secret
cd /opt/epic-secret

# 3. clone代码
git clone [Epic秘书仓库地址] .

# 4. 检查端口，选择一个未使用的端口（例如 8801）
netstat -tlnp
# 记录端口，后续配置使用
```

#### 1.2 基础配置
```bash
# 1. 复制配置模板
cp config.example.json config.json

# 2. 编辑配置文件，填写以下信息：
# - 监听端口
# - 飞书webhook URL
# - 飞书验证token（如果开启了签名）
# - 数据库连接信息（从现有数据库复制）
vim config.json
```

#### 1.3 网络配置
```nginx
# 新建Nginx配置：/etc/nginx/conf.d/epic.epicarena.cn.conf
server {
    listen 80;
    server_name epic.epicarena.cn;

    # 安全加固：IP白名单只放行飞书官方IP
    allow 103.170.108.0/23;
    allow 118.112.184.0/23;
    allow 119.123.0.0/16;
    allow 203.208.0.0/16;
    allow 127.0.0.1;
    deny all;

    location / {
        proxy_pass http://127.0.0.1:8801;  # 替换成选择的端口
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
# 申请HTTPS证书
sudo certbot --nginx -d epic.epicarena.cn

# 验证配置并重载
sudo nginx -t && sudo systemctl reload nginx
```

#### 1.4 安全加固
```bash
# 配置文件权限收紧
chmod 600 config.json

# 确认进程将以非root用户运行（在systemd配置中指定User）
```

#### 1.5 配置systemd守护进程
```ini
# 创建 /etc/systemd/system/epic-secret.service
[Unit]
Description=Epic Secretary Agent
After=network.target

[Service]
Type=simple
User=[用户名]
WorkingDirectory=/opt/epic-secret
ExecStart=/usr/bin/python /opt/epic-secret/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 启用并启动
sudo systemctl daemon-reload
sudo systemctl enable epic-secret
sudo systemctl start epic-secret
sudo systemctl status epic-secret  # 检查是否正常运行
```

#### 1.6 测试验证
- 从飞书发一条测试消息给Epic秘书机器人
- 确认能正常接收并回复
- 确认长期记忆读写正常
- 确认提醒功能正常

---

### 步骤2：部署workbuddy到阿里云并绑定飞书

流程和上面完全一样，只是目录、端口、域名不同。

#### 2.1 环境准备
```bash
sudo mkdir -p /opt/workbuddy
sudo chown [用户名]:[用户名] /opt/workbuddy
cd /opt/workbuddy
git clone [workbuddy仓库地址] .
# 选择一个未使用的端口，例如 8802
```

#### 2.2 基础配置
- 复制配置模板，填写端口、飞书webhook、数据库连接

#### 2.3 Nginx配置
```nginx
# /etc/nginx/conf.d/workbuddy.epicarena.cn.conf
server {
    listen 80;
    server_name workbuddy.epicarena.cn;

    # 安全加固：IP白名单
    allow 103.170.108.0/23;
    allow 118.112.184.0/23;
    allow 119.123.0.0/16;
    allow 203.208.0.0/16;
    allow 127.0.0.1;
    deny all;

    location / {
        proxy_pass http://127.0.0.1:8802;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

#### 2.4 HTTPS证书 + 安全加固 + systemd
- 和Epic秘书步骤完全一样
- 同样要做到：IP白名单、签名验证、权限600、非root运行

#### 2.5 测试验证
- 飞书发测试任务给workbuddy
- 确认能接收、处理、回复

---

## 四、安全加固检查清单（必须逐项检查）

| 检查项 | 要求 | 状态 |
|--------|------|------|
| 1 | Nginx只放行飞书官方IP + 127.0.0.1 | - |
| 2 | 开启飞书请求签名验证，拒绝非法请求 | - |
| 3 | config.json权限为600，只有运行用户能读 | - |
| 4 | 进程以普通用户运行，不是root | - |
| 5 | 所有请求都走Nginx反向代理，不直接暴露端口 | - |
| 6 | 全部使用HTTPS，不开放HTTP | - |

---

## 五、信息同步方案说明

### 当前策略（老袁确定）
- Epic秘书：部署在阿里云，长期记忆持久化存储，所有信息都存在阿里云数据库
- workbuddy：本地电脑是主要开发环境，阿里云部署飞书机器人只用于接收任务、推送进度
- 信息同步：如果token消耗高，可以不做双向同步
  - 老袁在飞书发任务 → 阿里云workbuddy机器人接收 → 推送到本地开发环境处理
  - 处理完成 → 结果返回阿里云机器人 → 推送到飞书
  - 长期记忆主要由Epic秘书维护，workbuddy不需要同步全部记忆
- 结论：按需同步，token优先，费token的话就不同步，不影响核心功能

---

## 六、数据库表单说明

### 当前数据库结构
项目已经有建好的数据库，包含以下主要表单：

| 表单 | 用途 | 说明 |
|------|------|------|
| memories | 长期记忆存储 | Epic秘书使用，存储分级长期记忆 |
| reminders | 提醒事项 | 存储提醒，支持已完成/未完成 |
| tasks | 任务记录 | 记录所有任务进度 |
| deployments | 部署信息 | 记录各智能体的部署配置 |

### 部署新智能体需要做
1. 不需要新建数据库，使用现有的即可
2. 在配置文件中填写正确的数据库连接信息（地址、端口、用户名、密码）
3. 每个智能体使用独立的配置表，不影响其他智能体
4. 数据库已经建好，直接连接使用即可

---

## 七、全流程联调测试

部署完成后，测试完整协作流程：

```
老袁在飞书提需求
    ↓
Epic秘书接收 → 梳理任务 → 分派给workbuddy
    ↓
workbuddy接收 → 开发完成 → 提交测试
    ↓
hermes接收 → 测试验证 → 出具测试报告
    ↓
结果返回飞书给老袁
```

### 测试checklist
- 消息链路通畅，每个环节都能收到
- 各个机器人回复正常，没有重复/丢失
- 安全加固生效，非飞书IP无法访问
- 签名验证正常，拒绝伪造请求
- 进程开机自启正常
- 内存CPU占用在合理范围

---

## 八、交付结果

完成所有部署测试后，交付：

1. 整理各智能体的：部署地址、端口、webhook配置
2. 出具安全加固检查报告，确认全部完成
3. 出具测试报告，确认全流程通畅
4. 汇报给老袁验收

---

## 九、交付时间

建议：一周内完成

---

## 十、总结

| 智能体 | 部署 | 飞书 | 安全加固 | 状态 |
|--------|------|------|----------|------|
| hermes | 阿里云 | 已绑定 | 需要复查 | 已完成 |
| Epic秘书 | 阿里云 | 需要做 | 需要做 | 待完成 |
| workbuddy | 阿里云 | 需要做 | 需要做 | 待完成 |
| arkclaw | 已直连 | 已绑定 | - | 已完成 |
