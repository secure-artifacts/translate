# AI 翻译助手

一个基于 Python 标准库 `tkinter` 的桌面翻译软件原型。

## 运行

```powershell
py -3 translator_app.py
```

首次运行会在同目录生成 `translator_config.json`，用于保存语言、模型、API KEY、置顶和回翻译设置。

## 发布与验证

当前发布版本：`v2.3.1`

- 组织仓库 Release：https://github.com/secure-artifacts/translate/releases/tag/v2.3.1
- 个人仓库 Release：https://github.com/ifghjb169-hash/translate/releases/tag/v2.3.1
- 构建产物：`AI-Translate-Assistant-v2.3.1-win-x64.zip`
- 可执行文件：解压后运行 `AI-Translate-Assistant.exe`
- 构建方式：GitHub Actions tag push 触发
- 构建证明：Release 产物由 GitHub Actions 上传，并通过 GitHub Attestation API 验证
- 组织仓库 SHA256：`55cab31e9ae3e0cfb4e97c7a24f1e3e98ba919b470f9fb9857f1d1c52aa01b62`
- 个人仓库 SHA256：`0041d7d1303d0cf3a0209344d15a075327261082ba7cf3e593fce2c2d0114755`

验证方式：

```powershell
# 下载 Release 产物后计算 SHA256
Get-FileHash -Algorithm SHA256 .\AI-Translate-Assistant-v2.3.1-win-x64.zip
```

也可以使用 GitHub CLI 验证软件来源：

```bash
gh attestation verify ./AI-Translate-Assistant-v2.3.1-win-x64.zip --repo secure-artifacts/translate
gh attestation verify ./AI-Translate-Assistant-v2.3.1-win-x64.zip --repo ifghjb169-hash/translate
```

## 已实现功能

- 翻译页分为输入框、译文框和回翻译小框，启动时输入框和译文框等高，三块高度可以拖动分隔条自由调整。
- 上下两个翻译框各显示三种可切换语言，并带更多语言下拉选择。
- 输入框支持默认麦克风语音输入，并可通过默认扬声器朗读输入内容。
- 译文框支持通过默认扬声器朗读翻译后的内容。
- 软件窗口和打包后的 EXE 使用羽毛图标。
- “交换语言”按钮位于输入框下方工具行，会对调上下语言；如果已有译文，也会把译文放回输入框方便继续翻译。
- 顶部使用等尺寸导航按钮：翻译、设置、文字、直译。
- 设置页支持窗口永远置顶。
- 支持选择 `AI 翻译` 或 `Google 翻译`；Google 模式只使用 Google 翻译。
- Google 翻译遇到临时限流时会尝试备用请求，并显示清晰错误提示，不再弹出 HTML 页面内容。
- AI 模式支持 Gemini 和 Groq AI；选择 Gemini 时只显示并使用 Gemini API KEY，选择 Groq 时只显示并使用 Groq API KEY。
- API KEY 可一行填写一个，并在当前密钥失败时自动尝试下一行。
- 设置页填写的 AI 平台、API KEY、模型、国家特色和性别会保存到本地配置，下次打开不用重新填写。
- “文字”页可分别设置输入框、译文框、回翻译框文字大小，也可设置软件界面显示语言。
- 软件界面显示语言支持中文简体、中文繁体、英语、日语、韩语、法语、德语、西班牙语、俄语，保存后下次启动完整生效。
- 软件系统界面文字会随窗口缩放自动调整。
- 软件关闭时会记住窗口尺寸，下次打开按上次关闭时的尺寸显示。
- 支持选择我的语言和对方语言，每组最多三种，已选语言会显示蓝色对勾。
- 语言列表已合并浏览器翻译扩展中的 127 种语言。
- 支持国家特色、我的性别、Gemini/Groq 模型选择。
- 支持开启或关闭回翻译。
- 普通模式下，输入框按第一次 `Enter` 开始翻译；译文完成后，第二次 `Enter` 会把译文输入到最近一次获得焦点的外部窗口输入框里；第三次 `Enter` 会尝试发送外部消息并清空本软件输入框。
- 输入框下方的“翻译”按钮与 `Enter` 使用相同流程；“复制译文”按钮位于译文框下方。
- 开启“直译”后，在 Teams、Facebook、记事本等外部输入框中按第一次 `Enter` 会读取当前输入、翻译并自动用译文替换聊天框内容；第二次 `Enter` 会发送消息并清空本软件输入框。
- 可使用同一个全局快捷键来回开启/关闭“直译”，默认是 `Alt+Q`，也可以在设置页底部自定义。
- 软件最小化后会显示悬浮按钮，可点击开启/关闭直译；悬浮按钮大小和亮起颜色可在设置页调整，支持预设颜色和自定义颜色代码。
- 使用外部输入时，先点一下 FB、Teams、记事本等软件里的聊天框/输入框，再回到翻译软件输入并翻译；软件会记住那个外部窗口。
- 按 `Shift+Enter` 可在输入框内换行。
- 窗口可自由调整大小，最小尺寸已放宽到更窄的 `330x240`。

## 模型列表

Gemini 默认列表：

- `gemini-2.0-flash`
- `gemini-2.5-flash`
- `gemini-3-flash-preview`
- `gemini-3-pro-preview`
- `gemini-3.1-flash-lite-preview`

Groq 默认列表：

- `llama-3.1-8b-instant`
- `llama-3.3-70b-versatile`
- `openai/gpt-oss-120b`
- `openai/gpt-oss-20b`

## 注意

API KEY 当前以明文保存在本地 `translator_config.json`。如果之后要正式发布，建议改成 Windows 凭据管理器或加密存储。
