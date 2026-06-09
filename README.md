# OfferRadar — 秋招信息自动收集 Agent

> 自动抓取校招信息 → LLM 智能分析匹配度 → Excel 跟踪表 → 每日播报 → 微信推送 → 邮箱监控
>
> **任何求职方向均可使用** | 只需修改一个配置文件 | macOS / Windows / Linux

---

## 运行效果

<details>
<summary><b>点击展开完整运行示例</b></summary>

```
$ python3 launcher.py run --lite

============================================================
  秋招Agent - 每日更新
  执行时间: 2026-06-07 23:05:52
  模式: 轻量 | 邮箱: 启用
============================================================

[Step 1/3] 开始抓取各公司招聘信息...
----------------------------------------
[INFO] 抓取字节跳动...
[INFO] 抓取华为...
  [OK] 百度: 6 条
[DONE] 共抓取 15 条岗位信息

[Step 2/3] 检查招聘邮件...
----------------------------------------
[INFO] 使用 Gmail API 模式
[INFO] 未找到新的未读招聘邮件

[Step 3/3] 生成每日播报 + 更新Excel...
----------------------------------------
[DONE] 播报已生成
[DONE] Excel已更新

[Push] 推送每日播报...
[OK] Server酱推送成功

============================================================
  执行完毕！ 岗位: 15条 | 邮箱: 已检查 | 推送: 已发送
============================================================
```

**生成的每日播报（含 AI 分析）：**

```markdown
# 秋招每日播报 - 2026-06-07

## 新增岗位
| 公司 | 岗位 | 来源 |
|------|------|------|
| 百度 | 2027AIDU-大模型算法工程师(J99938) | lite_scraper |
| 百度 | 2027AIDU-智能体算法工程师(J99969) | lite_scraper |
| 百度 | 2027AIDU-Agent应用全栈工程师(J99974) | lite_scraper |

## AI 分析
> 百度 AIDU 2027届已开启，"大模型算法工程师"和"智能体算法工程师"
> 与你的 RLHF/Agent 背景高度匹配，建议优先投递。
> 字节跳动 2027届项目已上线但尚未开放网申，持续关注。
```

**系统状态：**

```
$ python3 launcher.py status

  config.yaml:       已配置
  推送渠道:          serverchan
  LLM 接口:          deepseek-chat
  定时任务:          已启用 09:00
  监控公司: 47 家 | LLM应用算法工程师 | 2027届校招
```

</details>

---

## 运行成本

| 项目 | 费用 | 说明 |
|------|------|------|
| 本项目代码 | **免费开源** | MIT License |
| Python 3.9+ | 免费 | |
| LLM API（岗位分析） | **约 ¥0.1/天** | DeepSeek API，百万 token ≈ ¥1；不配置也能运行 |
| Server酱（微信推送） | 免费 | 每天 5 条额度 |
| 邮箱监控 | 免费 | IMAP 或 Gmail API |
| Playwright（可选） | 免费 | 不装也行，用轻量模式 |

**总结：几乎零成本。** 唯一付费项是 LLM 分析（每月 < ¥3），不配置则跳过，输出原始数据。

---

## 功能一览

| 功能 | 说明 | 是否需要 LLM |
|------|------|:---:|
| 岗位自动抓取 | 字节/百度/腾讯 API + 牛客聚合 + Cookie 登录抓取 | 否 |
| 智能去重 | SQLite 数据库自动去重，同一岗位不重复 | 否 |
| 投递状态管理 | 网页上直接切换：待关注→待投递→已投递→面试中→offer | 否 |
| 截止日期提醒 | 设置网申截止日期，3天内到期自动高亮提醒 | 否 |
| 每日播报 | 自动生成 Markdown 报告，可在网页查看 | 否 |
| AI 智能分析 | LLM 分析岗位匹配度 + 生成行动建议 | 是 |
| 简历匹配 | 粘贴简历 → 选岗位 → AI 分析命中/缺失技能 | 是 |
| 微信推送 | 通过 Server酱/PushPlus 推送到微信 | 否 |
| 邮箱监控 | 自动检查笔试/面试/offer 邮件（IMAP + Gmail） | 否 |
| 可视化仪表盘 | 图表统计 + 投递看板 + 配置管理，全在浏览器操作 | 否 |
| 定时执行 | 每天自动抓取+播报+推送（macOS/Windows/Linux） | 否 |

---

## 一键启动（推荐）

```bash
git clone https://github.com/dav627/OfferRadar.git
cd OfferRadar

# macOS / Linux
./start.sh

# Windows
start.bat
```

脚本会自动：检查 Python → 安装依赖 → 创建配置文件 → 初始化 → 启动可视化仪表盘。

首次运行会生成 `config.yaml`，脚本会提示你编辑它。填好后再次运行 `./start.sh` 即可启动。

> 仪表盘启动后，**所有配置都可以在网页界面上直接修改**（目标公司、岗位关键词、LLM Key、推送渠道、定时任务等），无需再手动编辑文件。

---

## 手动部署（完整步骤）

<details>
<summary>点击展开手动部署流程</summary>

### 第 1 步：安装

```bash
git clone https://github.com/dav627/OfferRadar.git
cd OfferRadar

# macOS / Linux
pip3 install openpyxl pyyaml

# Windows
pip install openpyxl pyyaml
```

> Windows 用户：下文的 `python3` 在你的系统上可能是 `python`。

### 第 2 步：创建配置文件

```bash
cp config.yaml.example config.yaml
```

打开 `config.yaml`，这是**唯一需要编辑的文件**，所有配置都在里面。按下面的顺序填写：

#### 2.1 设置你的求职画像（必填）

```yaml
profile:
  target_role: "算法工程师"          # 你的目标岗位名称
  graduation: "2027"                # 你的毕业届别

  # 搜索时包含这些关键词的岗位会被抓取（根据你的方向修改）
  keywords:
    - "大模型"
    - "LLM"
    - "NLP"
    - "算法"
    - "Agent"
    # 添加你关注的其他关键词...

  # 包含这些关键词的岗位会被排除（不想看到的方向）
  exclude_keywords:
    - "多模态"
    - "视觉"
    - "语音"
    # 根据需要增删...

  # 你的技能简介（LLM 分析匹配度时会参考，不会公开）
  bio: |
    计算机硕士，熟悉xxx、yyy，有zzz实习经验。
```

> **示例 - 前端方向：** keywords 改为 `["前端", "React", "Vue", "TypeScript", "Web"]`，exclude 改为 `["后端", "Java", "算法"]`
>
> **示例 - 后端方向：** keywords 改为 `["后端", "Java", "Go", "微服务", "分布式"]`

#### 2.2 设置推送渠道（推荐）

至少配一个，否则只能手动查看播报文件。推荐 Server酱（免费微信推送）：

1. 打开 https://sct.ftqq.com/ → 微信扫码注册 → 获取 SendKey
2. 填入 config.yaml：

```yaml
push:
  serverchan:
    enabled: true
    sendkey: "SCTxxx你的SendKey"
```

#### 2.3 设置 LLM 接口（可选，推荐）

配置后每日播报会包含 AI 智能分析（岗位匹配度评分 + 行动建议）。不配则跳过。

1. 打开 https://platform.deepseek.com/ → 注册 → 创建 API Key
2. 填入 config.yaml：

```yaml
llm:
  api_key: "sk-你的key"
  base_url: "https://api.deepseek.com/v1"
  model: "deepseek-chat"
```

<details>
<summary>其他 LLM 提供商</summary>

| 提供商 | base_url | model | 备注 |
|--------|----------|-------|------|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` | 最便宜 |
| 智谱AI | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` | 免费额度 |
| Moonshot | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` | |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | 需外币卡 |
| 本地 Ollama | `http://localhost:11434/v1` | `qwen2.5:7b` | 完全免费 |

支持任何兼容 OpenAI 格式的 API。

</details>

#### 2.4 设置邮箱监控（可选）

监控笔试通知、面试邀请、offer 通知等招聘相关邮件。

<details>
<summary><b>方式 A：163 / QQ / Outlook 等国内邮箱（IMAP，简单）</b></summary>

**获取授权码：**

| 邮箱 | 路径 | 说明 |
|------|------|------|
| **163** | 设置 → POP3/SMTP/IMAP → 开启IMAP | 首次会生成授权码 |
| **QQ** | 设置 → 账户 → 开启IMAP | 发短信验证后获取 |
| **Outlook** | 直接用登录密码 | 无需授权码 |

**填入 config.yaml：**

```yaml
email:
  method: "imap"
  address: "yourname@163.com"
  password: "你的授权码"
  provider: "163"                 # 或 qq / outlook / 126
```

</details>

<details>
<summary><b>方式 B：Gmail（OAuth API，较复杂）</b></summary>

1. 打开 https://console.cloud.google.com/ → 新建项目 → 启用 Gmail API
2. **Google Auth Platform** → 配置 OAuth 同意屏幕 → 添加你的 Gmail 为**测试用户**
3. 创建 **桌面应用** 类型的 OAuth 客户端 → 记下客户端 ID 和密钥
4. 在项目根目录创建 `credentials.json`：
   ```json
   {
     "installed": {
       "client_id": "你的ID.apps.googleusercontent.com",
       "client_secret": "你的密钥",
       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
       "token_uri": "https://oauth2.googleapis.com/token",
       "redirect_uris": ["http://localhost"]
     }
   }
   ```
5. 运行 `python3 launcher.py gmail-auth`，复制链接到浏览器授权
6. 国内网络需在 config.yaml 配置代理：
   ```yaml
   proxy:
     http: "http://127.0.0.1:7897"
     https: "http://127.0.0.1:7897"
   ```

</details>

#### 2.5 设置网络代理（如需要）

如果你在国内且需要访问 Google 服务（Gmail / Playwright CDN）：

```yaml
proxy:
  http: "http://127.0.0.1:7897"     # 你的代理端口
  https: "http://127.0.0.1:7897"
```

### 第 3 步：初始化

```bash
python3 launcher.py init
```

会自动检查依赖、创建 Excel 投递跟踪表、创建数据目录。

### 第 4 步：首次运行

```bash
# 先跑一次看看效果（不推送）
python3 launcher.py run --lite --no-email --no-push

# 确认没问题后，完整运行（含推送）
python3 launcher.py run --lite
```

### 第 5 步：设置每天自动执行

```bash
python3 launcher.py schedule --on             # 开启（默认每天 09:00）
python3 launcher.py schedule --time 08:30     # 改时间
python3 launcher.py schedule --off            # 关闭
```

自动检测操作系统：macOS 用 launchd，Windows 用任务计划程序，Linux 用 crontab。

> 定时任务也可以在仪表盘的「系统配置」页面直接设置。

</details>

---

## 自定义目标公司

编辑根目录的 `公司清单.json`：

**添加公司：**
```json
{"name": "新公司", "tier": "A", "category": "AI公司", "aliases": ["NewCo"]}
```

**删除公司：** 删掉对应行即可。

**梯队说明：** `tier` 影响优先级和 Excel 排序：

| tier | 含义 | 示例 |
|------|------|------|
| S | 最高优先级 | 字节、腾讯、阿里、百度 |
| A | 高优先级 | 快手、小红书、DeepSeek |
| B | 普通关注 | B站、携程、OPPO |
| C | 备选 | 搜狐等 |

**分类标签 category：** `互联网大厂` / `AI公司` / `中大型互联网` / `手机/硬件` / `国企/运营商` / `其他`

> 公司清单预置了 47 家常见公司。你可以全部删掉换成自己的列表，格式不变即可。

---

## 命令一览

| 命令 | 说明 |
|------|------|
| `launcher.py run` | 完整执行（抓取+邮箱+分析+播报+推送） |
| `launcher.py run --lite` | 轻量模式（推荐日常使用，无需 Playwright） |
| `launcher.py run --no-email` | 跳过邮箱检查 |
| `launcher.py run --no-push` | 跳过推送（调试用） |
| `launcher.py init` | 首次初始化 |
| `launcher.py status` | 查看系统状态 |
| `launcher.py test-push` | 发送测试推送 |
| `launcher.py test-llm` | 测试 LLM 接口 |
| `launcher.py gmail-auth` | Gmail 授权 |
| `launcher.py schedule --on` | 开启每日定时 |
| `launcher.py schedule --off` | 关闭定时 |
| `launcher.py schedule --time HH:MM` | 改执行时间 |

---

## 目录结构

```
OfferRadar/
├── start.sh                 # 一键启动（macOS/Linux）
├── start.bat                # 一键启动（Windows）
├── launcher.py              # 命令行入口
├── config.yaml.example      # 配置模板
├── 公司清单.json             # 目标公司（可自由增删）
├── README.md
│
├── core/                    # 业务模块（无需直接操作）
│   ├── config.py            # 配置加载
│   ├── scraper.py           # Playwright 抓取
│   ├── scraper_lite.py      # 轻量抓取
│   ├── report.py            # 播报 + Excel
│   ├── email_monitor.py     # 邮箱监控（Gmail + IMAP）
│   ├── gmail.py             # Gmail API
│   ├── notifier.py          # 推送
│   ├── llm.py               # LLM 分析
│   ├── daily.py             # 主流程
│   └── auto_apply.py        # 自动投递（实验性）
│
├── scripts/
│   ├── setup_schedule.sh    # macOS/Linux 定时
│   └── setup_schedule.bat   # Windows 定时
│
└── data/                    # 运行时数据（gitignore）
    ├── 秋招投递跟踪表.xlsx
    ├── 抓取结果/
    ├── 每日播报/
    └── email_results/
```

---

## 常见问题

<details>
<summary><b>Playwright Chromium 下载失败（ETIMEDOUT）</b></summary>

国内网络无法直连 `cdn.playwright.dev`。

- **方案 A（推荐）：** 用轻量模式，完全不需要 Playwright：`python3 launcher.py run --lite`
- **方案 B：** 不装 Chromium，用系统 Chrome（项目已自动适配）
- **方案 C：** 挂代理下载：`HTTPS_PROXY=http://127.0.0.1:7897 python3 -m playwright install chromium`

</details>

<details>
<summary><b>Gmail OAuth 报 403 access_denied</b></summary>

OAuth 应用处于测试状态，需要把你的 Gmail 添加为测试用户：
Google Cloud Console → Google Auth Platform → 目标对象 → + Add users → 填入你的 Gmail

</details>

<details>
<summary><b>Gmail API 调用超时（socket.timeout）</b></summary>

Python 的 httplib2 不读系统代理。在 config.yaml 中配置 proxy 段即可，项目会自动注入。

</details>

<details>
<summary><b>Gmail 授权时浏览器没弹出</b></summary>

用 `python3 launcher.py gmail-auth`，它会打印链接而非自动打开浏览器，手动复制即可。

</details>

---

## License

MIT
