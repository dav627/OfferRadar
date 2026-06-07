# OfferRadar — 秋招信息自动收集 Agent

> 自动抓取各大公司校招信息 → LLM 智能分析匹配度 → Excel 跟踪表 → 每日播报 → 微信推送 → 邮箱监控
>
> **跨平台支持：macOS / Windows / Linux**

## 运行效果展示

<details>
<summary><b>📋 一次完整运行示例（点击展开）</b></summary>

### 1. 启动运行

```
$ python3 launcher.py run --lite

============================================================
  秋招Agent - 每日更新
  执行时间: 2026-06-07 23:05:52
  模式: 轻量 | 邮箱: 启用
============================================================

[Step 1/3] 开始抓取各公司招聘信息...
----------------------------------------
[INFO] 轻量级抓取开始
[INFO] 抓取字节跳动...
[INFO] 抓取华为...
[INFO] 并发抓取其他公司...
  [OK] 百度: 6 条
[DONE] 共抓取 15 条岗位信息

[Step 2/3] 检查招聘邮件...
----------------------------------------
[INFO] 使用 Gmail API 模式
[INFO] 未找到新的未读招聘邮件

[Step 3/3] 生成每日播报 + 更新Excel...
----------------------------------------
[DONE] 播报已生成: data/每日播报/2026-06-07.md
[DONE] Excel已更新

[Push] 推送每日播报...
----------------------------------------
[OK] Server酱推送成功

============================================================
  执行完毕！
  - 岗位: 15 条
  - 邮箱: 已检查（Gmail）
  - 推送: 已发送（微信）
  - 播报: 每日播报/2026-06-07.md
============================================================
```

### 2. 生成的每日播报（Markdown）

```markdown
# 秋招每日播报 - 2026-06-07

## 今日概况

| 指标 | 数值 |
|------|------|
| 抓取岗位总数 | 15 |
| 新增岗位数 | 6 |
| 涉及公司数 | 2 |

## 新增岗位

| 公司 | 岗位 | 来源 |
|------|------|------|
| 百度 | 2027AIDU-大模型算法工程师(J99938) | lite_scraper |
| 百度 | 2027AIDU-大模型Infra工程师(J99967) | lite_scraper |
| 百度 | 2027AIDU-智能体算法工程师(J99969) | lite_scraper |
| 百度 | 2027AIDU-Agent应用全栈工程师(J99974) | lite_scraper |

## AI 分析（配置 LLM API 后自动生成）

> 今日重点：百度 AIDU 2027届校招已开启，其中"大模型算法工程师"和
> "智能体算法工程师"与你的 RLHF/Agent 背景高度匹配，建议优先投递。
> 字节跳动 2027届项目已上线但尚未开放网申，持续关注。
>
> 行动建议：
> 1. 立即投递百度 J99938（大模型算法）和 J99969（智能体算法）
> 2. DeepSeek/智谱/月之暗面等AI公司滚动招聘中，本周可投
> 3. 大厂提前批预计7月开放，准备简历针对性版本
```

### 3. 抓取到的实际岗位数据

```
字节跳动 | [AI应用] 基于多Sensor、多模态的大模型应用探索
字节跳动 | [搜索推荐广告] LLM 技术在广告模型研究与应用
字节跳动 | [搜索推荐广告] 面向广告场景的生成式推荐大模型
字节跳动 | [AI Safety] 大模型安全与隐私
字节跳动 | [工程架构] 面向LLM的下一代智能云基础架构
字节跳动 | [招聘信息] 面向 2027 届毕业生，提供转正机会
百度     | 2027AIDU-大模型算法工程师(J99938)        ← 高匹配
百度     | 2027AIDU-大模型Infra工程师(J99967)
百度     | 2027AIDU-智能体算法工程师(J99969)         ← 高匹配
百度     | 2027AIDU-Agent应用全栈工程师(J99974)      ← 高匹配
```

### 4. 系统状态

```
$ python3 launcher.py status

=== 秋招Agent 系统状态 ===

  config.yaml:       已配置
  Gmail credentials: 已配置
  Gmail token:       已授权
  投递跟踪表:        已生成
  推送渠道:          serverchan
  LLM 接口:          deepseek-chat @ https://api.deepseek.com/v1
  代理设置:          http://127.0.0.1:7897
  定时任务:          已启用 09:00

  最近抓取: 2026-06-07T23:05 | 15 条
  最近播报: 2026-06-07

  监控公司: 47 家 | LLM应用算法 | 仅校招2027届
```

### 5. 微信推送效果

每天自动推送到微信（通过 Server酱），内容即每日播报的精简版。

</details>

---

## 运行成本

| 项目 | 费用 | 说明 |
|------|------|------|
| 本项目代码 | **免费开源** | MIT License |
| Python 3.9+ | 免费 | |
| LLM API（岗位分析） | **约 ¥0.1/天** | DeepSeek API，百万 token ≈ ¥1，每次分析约用 2K token |
| Server酱（微信推送） | 免费 | 每天 5 条额度，完全够用 |
| Gmail API | 免费 | 个人用量远低于免费配额 |
| Google Cloud 项目 | 免费 | 不需要绑定信用卡 |
| Playwright（可选） | 免费 | 也可以不装，用轻量抓取模式 |

**总结：几乎零成本。** LLM 分析是唯一付费项，使用 DeepSeek API 每月不到 ¥3。也可以不配置 LLM，系统会跳过智能分析，仅输出原始数据。

---

## 功能架构

```
┌─────────────────────────────────────────────────┐
│                 launcher.py                      │
│              （统一启动器入口）                     │
├──────┬──────┬──────┬──────┬──────┬───────────────┤
│ run  │ init │status│sched │gmail │  test-push    │
│      │      │      │ ule  │-auth │               │
└──┬───┴──────┴──────┴──┬───┴──┬───┴───────────────┘
   │                    │      │
   ▼                    ▼      ▼
┌──────────┐   ┌────────────┐ ┌──────────────┐
│ 信息抓取  │   │ 定时任务    │ │ Gmail 监控   │
│scraper.py│   │macOS       │ │gmail_monitor │
│scraper   │   │launchd     │ │   .py        │
│ _lite.py │   └────────────┘ └──────────────┘
└────┬─────┘
     ▼
┌──────────┐    ┌──────────────┐    ┌────────────┐
│ Excel    │───▶│  每日播报     │───▶│ 微信/QQ    │
│ 跟踪表   │    │ update_report│    │  推送       │
│          │    │   .py        │    │ notifier.py│
└──────────┘    └──────────────┘    └────────────┘
```

**岗位过滤策略：**
- 目标：LLM应用算法（RLHF/DPO/RAG/Agent/对齐/SFT 等）
- 排除：多模态、基座模型预训练、计算机视觉、语音
- 范围：仅校园招聘（2027届），不含社招

---

## 快速开始

### 1. 克隆 & 安装依赖

```bash
git clone https://github.com/IDIOT01/OfferRadar.git
cd OfferRadar

# macOS / Linux
pip3 install openpyxl pyyaml

# Windows（cmd 或 PowerShell）
pip install openpyxl pyyaml

# 可选：完整抓取需要 Playwright（跨平台）
pip3 install playwright && python3 -m playwright install chromium
```

> **Windows 用户提示：** 下文的 `python3` 命令在 Windows 上可能需要用 `python` 替代。

### 2. 配置

```bash
# 复制配置模板（所有配置集中在这一个文件）
cp config.yaml.example config.yaml

# 编辑 config.yaml，按注释说明填写
vim config.yaml
```

最少只需填 `push.serverchan.sendkey`（微信推送）就能跑起来。

### 3. 初始化 & 运行

```bash
# 初始化（生成 Excel 等）
python3 launcher.py init

# 首次运行（轻量模式，无需 Gmail）
python3 launcher.py run --lite --no-gmail --no-push

# 验证推送
python3 launcher.py test-push

# 查看系统状态
python3 launcher.py status
```

---

## 详细配置

### LLM 接口（智能分析）

LLM 用于：岗位匹配度评分、JD 关键信息提取、每日播报的自然语言总结。

**推荐 DeepSeek API**（最便宜，百万 token ≈ ¥1）：

1. 访问 https://platform.deepseek.com/ 注册
2. 创建 API Key
3. 写入 `.env`：
   ```
   LLM_API_KEY=sk-你的key
   LLM_BASE_URL=https://api.deepseek.com/v1
   LLM_MODEL=deepseek-chat
   ```
4. 测试：`python3 launcher.py test-llm`

**也支持其他兼容 OpenAI 格式的 API：**

| 提供商 | BASE_URL | MODEL | 备注 |
|--------|----------|-------|------|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` | 最便宜 |
| 智谱AI | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` | 免费额度 |
| Moonshot | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` | |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | 需外币卡 |
| 本地 Ollama | `http://localhost:11434/v1` | `qwen2.5:7b` | 完全免费 |

> 不配置 LLM 也能正常运行，只是跳过智能分析，输出原始数据表格。

### 微信推送（Server酱）

1. 访问 https://sct.ftqq.com/ 微信扫码注册
2. 获取 SendKey（格式 `SCTxxx`）
3. 写入 `config.yaml`：
   ```yaml
   push:
     serverchan:
       enabled: true
       sendkey: "SCTxxx你的SendKey"
   ```
4. 测试：`python3 launcher.py test-push`

### 邮箱监控

监控笔试通知、面试邀请、offer 通知等招聘邮件。支持两种方式：

#### 方式 A：163 / QQ / Outlook 等国内邮箱（IMAP，推荐）

配置最简单，只需邮箱地址 + 授权码。

**第 1 步：获取授权码**

| 邮箱 | 操作路径 | 说明 |
|------|----------|------|
| **163** | 设置 → POP3/SMTP/IMAP → 开启IMAP服务 | 首次开启会生成授权码，务必记下 |
| **QQ** | 设置 → 账户 → POP3/IMAP/SMTP/Exchange/CardDAV → 开启IMAP | 需要发短信验证，然后获取授权码 |
| **Outlook** | 直接使用登录密码 | 无需单独授权码 |
| **126** | 设置 → POP3/SMTP/IMAP → 开启IMAP | 同 163 |

**第 2 步：写入 config.yaml**

```yaml
email:
  method: "imap"
  address: "yourname@163.com"       # 你的邮箱
  password: "ABCDEFGHIJKLMN"        # 授权码（不是登录密码！）
  provider: "163"                   # 可选: 163 / qq / outlook / 126 / yeah / sina / gmail
```

> `provider` 用于自动匹配 IMAP 服务器地址。如果匹配不上，手动填 `imap_host` 和 `imap_port`。

#### 方式 B：Gmail（OAuth API）

更安全但配置较复杂，适合主力使用 Gmail 的用户。

**第 1 步：创建 Google Cloud 项目**

1. 打开 https://console.cloud.google.com/ → 新建项目
2. **API和服务** → **库** → 搜索 **Gmail API** → **启用**

**第 2 步：配置 OAuth 同意屏幕**

> 当前（2026年）入口可能在 **Google Auth Platform** 页面。

1. 左侧 → **Google Auth Platform**（或 **OAuth 同意屏幕**）
2. 填写应用名称、邮箱
3. **受众群体/目标对象** → 选 **外部**
4. **重要：** 添加你的 Gmail 为 **测试用户**（否则 403 access_denied）

**第 3 步：创建 OAuth 凭据**

1. 左侧 → **客户端** → **+ 创建客户端** → 桌面应用
2. 记下 **客户端 ID** 和 **密钥**

**第 4 步：生成 credentials.json**

在项目根目录创建 `credentials.json`：

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

**第 5 步：授权**

```bash
python3 launcher.py gmail-auth
# 复制终端打印的链接到浏览器 → 登录 → 粘贴授权码回终端
```

**第 6 步：config.yaml**（可选，默认自动检测）

```yaml
email:
  method: "gmail_api"
```

**Gmail 代理：** 国内网络需在 `config.yaml` 配置代理才能连接 googleapis.com：

```yaml
proxy:
  http: "http://127.0.0.1:7897"
  https: "http://127.0.0.1:7897"
```

### 自定义公司清单

编辑 `公司清单.json`，你可以：

**添加公司：** 在 `companies` 数组中追加：
```json
{"name": "新公司", "tier": "A", "category": "AI公司", "aliases": ["英文名"]}
```

**删除公司：** 直接删除对应行。

**调整梯队：** `tier` 字段决定优先级（S > A > B > C），影响 Excel 排序和播报顺序。

**分类说明：**
| category | 示例 |
|----------|------|
| 互联网大厂 | 字节、腾讯、阿里、百度 |
| AI公司 | DeepSeek、智谱、月之暗面 |
| 中大型互联网 | B站、得物、携程 |
| 手机/硬件 | OPPO、vivo、小米 |
| 国企/运营商 | 中国移动、浪潮 |

**调整岗位过滤关键词：** 修改 `meta.keywords`（包含词）和 `meta.exclude_keywords`（排除词）：
```json
{
  "meta": {
    "keywords": ["大模型算法", "LLM算法", "RAG算法", "Agent算法", "..."],
    "exclude_keywords": ["多模态", "预训练", "视觉", "语音", "..."]
  }
}
```

### 定时执行（macOS / Windows / Linux）

```bash
python3 launcher.py schedule --on           # 开启（每天 09:00）
python3 launcher.py schedule --time 08:30   # 改时间
python3 launcher.py schedule --off          # 关闭
python3 launcher.py schedule               # 查看状态
```

自动检测操作系统，使用对应的定时方案：

| 系统 | 底层实现 | 说明 |
|------|----------|------|
| **macOS** | launchd (plist) | 开机自启，系统原生 |
| **Windows** | 任务计划程序 (schtasks) | 需管理员权限创建 |
| **Linux** | crontab | 标准 cron job |

> **Windows 注意事项：**
> - 首次运行 `schedule --on` 可能需要以管理员身份打开终端
> - Python 命令可能是 `python` 而非 `python3`，根据你的安装情况调整

---

## 启动器命令一览

```bash
python3 launcher.py run              # 完整执行
python3 launcher.py run --lite       # 轻量模式（推荐日常使用）
python3 launcher.py run --no-email   # 跳过邮箱
python3 launcher.py run --no-push    # 跳过推送

python3 launcher.py init             # 首次初始化
python3 launcher.py status           # 查看状态
python3 launcher.py test-push        # 测试推送
python3 launcher.py test-llm         # 测试 LLM 接口
python3 launcher.py gmail-auth       # Gmail 授权

python3 launcher.py schedule         # 查看定时任务
python3 launcher.py schedule --on    # 开启
python3 launcher.py schedule --off   # 关闭
python3 launcher.py schedule --time HH:MM  # 改时间
```

---

## 目录结构

```
OfferRadar/
├── launcher.py              # 唯一入口（所有操作从这里启动）
├── config.yaml.example      # 配置模板（复制为 config.yaml 后编辑）
├── 公司清单.json             # 目标公司列表（可自行增删）
├── README.md
│
├── core/                    # 业务模块（无需直接操作）
│   ├── config.py            # 配置加载器
│   ├── scraper.py           # Playwright 全功能抓取
│   ├── scraper_lite.py      # 轻量抓取（无需浏览器）
│   ├── report.py            # 播报生成 + Excel 更新
│   ├── email_monitor.py     # 统一邮件监控（Gmail + IMAP）
│   ├── gmail.py             # Gmail API + OAuth 授权
│   ├── notifier.py          # 微信/QQ 推送
│   ├── llm.py               # LLM 智能分析
│   ├── daily.py             # 每日执行主流程
│   └── auto_apply.py        # 自动投递（实验性）
│
├── scripts/
│   ├── setup_schedule.sh    # macOS/Linux 定时任务
│   └── setup_schedule.bat   # Windows 定时任务
│
├── config.yaml              # 你的配置（不提交 git）
├── credentials.json         # Gmail 凭据（不提交）
├── token.json               # Gmail token（不提交）
└── data/                    # 运行时数据（不提交）
    ├── 秋招投递跟踪表.xlsx
    ├── 抓取结果/
    ├── 每日播报/
    └── email_results/
```

---

## 常见问题 & 踩坑记录

### Q: Playwright Chromium 下载失败（ETIMEDOUT / ENOTFOUND）

**现象：** `python3 -m playwright install chromium` 报错 `cdn.playwright.dev` 超时或无法解析。

**原因：** 国内网络无法直连 Playwright CDN（Azure 节点）。

**解决方案：**
- **方案 A（推荐）：** 不装 Chromium，使用系统自带的 Chrome。本项目的 `scraper.py` 已配置为优先使用系统 Chrome（`channel="chrome"`），只需安装 Google Chrome 浏览器即可。
- **方案 B：** 挂代理后下载：`HTTPS_PROXY=http://127.0.0.1:7897 python3 -m playwright install chromium`
- **方案 C：** 使用轻量抓取器 `scraper_lite.py`，完全不需要浏览器：`python3 launcher.py run --lite`

### Q: Gmail OAuth 报 403 access_denied（"尚未完成 Google 验证流程"）

**现象：** 浏览器授权时显示"禁止访问：xxx 尚未完成 Google 验证流程"。

**原因：** 你的 OAuth 应用处于"测试"状态，需要将自己的 Gmail 添加为测试用户。

**解决方案：**
1. Google Cloud Console → **Google Auth Platform**（左侧菜单）
2. 点 **目标对象**（或 **受众群体**）
3. **测试用户** 区域 → **+ Add users** → 输入你的 Gmail 地址 → 保存
4. 重新运行 `python3 launcher.py gmail-auth`

### Q: Gmail API 调用超时

**现象：** 授权成功但 `gmail_monitor.py` 运行时报 `socket.timeout`。

**原因：** Python 的 `httplib2` 库不读取系统代理设置和 `HTTP_PROXY` 环境变量。

**解决方案：** 在 `.env` 中配置代理（本项目已通过 `config_loader.py` 自动将代理注入 httplib2）：
```
HTTP_PROXY=http://127.0.0.1:7897
HTTPS_PROXY=http://127.0.0.1:7897
```

### Q: Gmail 授权时浏览器没有弹出

**现象：** 运行 `gmail_monitor.py --auth` 后终端无输出，浏览器未弹出。

**解决方案：** 使用专用的手动授权脚本：
```bash
python3 launcher.py gmail-auth
```
它会打印授权链接而不是自动打开浏览器，手动复制到浏览器即可。

### Q: 如何自定义监控的公司列表？

编辑 `公司清单.json`，按格式添加：
```json
{"name": "公司名", "tier": "A", "category": "AI公司", "aliases": ["英文名"]}
```

---

## License

MIT
