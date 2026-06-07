# 2027 秋招 LLM应用算法 — 自动信息收集 Agent

> 自动抓取各大公司校招信息 → LLM 智能分析匹配度 → Excel 跟踪表 → 每日播报 → 微信推送 → Gmail 监控

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
git clone https://github.com/IDIOT01/2027LLM-Agent.git
cd 2027LLM-Agent

pip3 install openpyxl
# 可选：完整抓取需要 Playwright
pip3 install playwright && python3 -m playwright install chromium
```

### 2. 配置

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env，至少填写一个推送渠道
# 推荐 Server酱（免费微信推送）：https://sct.ftqq.com/ 注册获取 SendKey
vim .env
```

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
3. 写入 `.env`：
   ```
   SERVERCHAN_SENDKEY=SCTxxx你的SendKey
   ```
4. 测试：`python3 launcher.py test-push`

### Gmail 邮件监控

监控笔试通知、面试邀请、offer 通知等招聘邮件。

#### 步骤 1：创建 Google Cloud 项目

1. 打开 https://console.cloud.google.com/
2. 新建项目（名称随意）
3. 左侧 → **API和服务** → **库** → 搜索 **Gmail API** → **启用**

#### 步骤 2：配置 OAuth 同意屏幕

> Google Cloud Console 界面会不定期变化。当前（2026年）入口可能在 **Google Auth Platform** 页面。

1. 左侧 → **Google Auth Platform**（或 **API和服务 → OAuth 同意屏幕**）
2. 填写应用名称、邮箱等基本信息
3. **受众群体/目标对象** 页面 → 选择 **外部**
4. **重要：** 添加你自己的 Gmail 地址为 **测试用户**（否则会报 403 access_denied）

#### 步骤 3：创建 OAuth 凭据

1. 左侧 → **客户端**（或 **凭据**）
2. **+ 创建客户端** → 应用类型选 **桌面应用**
3. 创建后记下 **客户端 ID** 和 **客户端密钥**

#### 步骤 4：生成 credentials.json

手动创建 `credentials.json`（在项目根目录下）：

```json
{
  "installed": {
    "client_id": "你的客户端ID.apps.googleusercontent.com",
    "client_secret": "你的客户端密钥",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "redirect_uris": ["http://localhost"]
  }
}
```

#### 步骤 5：授权

```bash
python3 launcher.py gmail-auth
```

终端会打印一个链接 → 复制到浏览器打开 → 登录 Gmail → 允许权限 → 把页面上的**授权码**粘贴回终端。

#### Gmail 代理设置

如果你的网络无法直连 `googleapis.com`（如国内网络），需要在 `.env` 中配置代理：

```
HTTP_PROXY=http://127.0.0.1:7897
HTTPS_PROXY=http://127.0.0.1:7897
```

端口号根据你的代理软件（Clash/V2Ray 等）实际端口填写。

### 定时执行（macOS）

```bash
# 开启（默认每天 09:00）
python3 launcher.py schedule --on

# 改时间
python3 launcher.py schedule --time 08:30

# 关闭
python3 launcher.py schedule --off

# 查看状态
python3 launcher.py schedule
```

---

## 启动器命令一览

```bash
python3 launcher.py run              # 完整执行
python3 launcher.py run --lite       # 轻量模式（推荐日常使用）
python3 launcher.py run --no-gmail   # 跳过 Gmail
python3 launcher.py run --no-push    # 跳过推送

python3 launcher.py init             # 首次初始化
python3 launcher.py status           # 查看状态
python3 launcher.py test-push        # 测试推送
python3 launcher.py gmail-auth       # Gmail 授权

python3 launcher.py schedule         # 查看定时任务
python3 launcher.py schedule --on    # 开启
python3 launcher.py schedule --off   # 关闭
python3 launcher.py schedule --time HH:MM  # 改时间
```

---

## 目录结构

```
2027LLM-Agent/
├── launcher.py          # 统一启动器（所有操作的入口）
├── run_daily.py         # 每日执行主流程
├── scraper.py           # Playwright 全功能抓取器
├── scraper_lite.py      # 轻量抓取器（无需浏览器，推荐）
├── update_report.py     # 播报生成 + Excel 更新
├── gmail_monitor.py     # Gmail 招聘邮件监控
├── gmail_auth.py        # Gmail 手动授权脚本
├── notifier.py          # 微信/QQ 推送
├── llm_analyzer.py      # LLM 智能分析（匹配评分+播报总结）
├── auto_apply.py        # 自动投递框架（实验性）
├── config_loader.py     # 统一配置加载器
├── setup_schedule.sh    # macOS launchd 定时任务
├── config.json          # 推送渠道配置（备选，优先用 .env）
├── schedule.json        # 定时任务配置
├── 公司清单.json         # 监控的目标公司（46 家）
├── .env.example         # 环境变量模板
├── .env                 # 你的实际配置（不提交到 git）
├── credentials.json     # Gmail OAuth 凭据（不提交）
├── token.json           # Gmail 授权 token（不提交）
├── 秋招投递跟踪表.xlsx   # 投递数据（自动生成，不提交）
├── 抓取结果/            # 抓取原始数据（不提交）
├── 每日播报/            # 每日报告（不提交）
└── gmail_results/       # 邮件监控结果（不提交）
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
