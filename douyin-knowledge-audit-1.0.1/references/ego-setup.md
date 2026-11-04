# ego 接入：让 Agent 长一双手

## 为什么值得单独装一套

| 维度 | ego lite | 空白会话的自动化浏览器 |
|---|---|---|
| 登录态 | 继承你 Chrome 的登录、Cookie、扩展 | 每次重新登 |
| 抢不抢窗口 | 在独立 Space 跑，你的标签页不动 | 抢窗口或另开浏览器 |
| 驱动方式 | 写一段脚本一次跑完多步 | CLI 一条条来回敲 |
| 并行 | 一个浏览器多个 Space 同时干 | 串行 |

一句话判断：**要读网页，随便哪个都行；要在你的后台里办事，必须继承登录态。**

ego lite 是 MIT 协议（Copyright (c) 2026 CitroLabs），开源仓库 `citrolabs/ego-lite`。本文档只记录接入方法与踩坑，不分发其二进制。

## 安装三步

**1. 装 App**：官网下载对应架构的 dmg，拖进「应用程序」。Apple Silicon 选 arm64。

**2. 建命令入口**：App 内的 `ego-browser` 是可执行 helper，把它软链到 PATH 目录。

```bash
ln -sf "/Applications/ego lite.app/Contents/Frameworks/ego Framework.framework/Versions/<版本>/Helpers/ego-browser" ~/.local/bin/ego-browser
~/.local/bin/ego-browser --version   # 有输出即通
```

版本号会变，先 `find "/Applications/ego lite.app" -name ego-browser` 定位真实路径，不要照抄。

**3. 装驱动说明**：把官方 skill 目录放进 Agent 会加载的技能目录（如 `~/.workbuddy/skills/ego-browser`）。它的 SKILL.md 第一句是"任何浏览器任务开始前先跑 `ego-browser skill`"——**这句要照做**，因为输出的是与当前版本匹配的手册，比任何第三方总结都准。

## 五个真踩到的坑

### 坑 1｜图形引导没走完，CLI 全废

现象：任何命令都返回 `Please complete the onboarding process first. A setup window has opened...`
根因：首次启动的引导必须人工点击（含"是否从 Chrome 导入数据"）。
处置：**Agent 不要尝试代点**（系统会以辅助功能权限拦下）。停下，请人点完。

### 坑 2｜导入数据这个选项，决定后续一切

引导里问"要不要从 Chrome 导入"。**选导入**，登录态、Cookie、书签一次带过来；选跳过，你得到的是一个全新空浏览器，等于没用。
自检：`ego-browser import list` 能看到来源档案（邮箱、Chrome 版本）才算导入成功。

### 坑 3｜PATH 里找不到命令

现象：终端能跑，Agent 跑就 `command not found`。
根因：`~/.local/bin` 在交互式 zsh 的 PATH 里，但 Agent 的执行环境不继承它。
处置：调用前 `export PATH="$HOME/.local/bin:$PATH"`，或直接用绝对路径。把绝对路径写进技能备注，不指望环境。

### 坑 4｜`raw.githubusercontent.com` 拉不动

现象：`curl` 返回 000、30 秒超时。
根因：该域名在部分网络下不可达；`api.github.com` 与 `codeload.github.com` 通常正常。
处置：走 GitHub contents API 取 base64 再解码，或用 `codeload` 拉 tarball：

```bash
curl -sL "https://codeload.github.com/<owner>/<repo>/tar.gz/refs/heads/main" -o r.tgz
```

### 坑 5｜元素在 DOM 里，但点不动

现象：`zero-sized bounding box`，或点击无反应。
根因：**元素被排在默认视口下沿之外，尺寸算出来是 0**，不是选择器错。
处置：先放大视口再点。

```js
await page.cdp("Emulation.setDeviceMetricsOverride",
  { width: 1512, height: 1040, deviceScaleFactor: 1, mobile: false });
```

先怀疑视口，再怀疑选择器。这条省下的时间比前四条加起来都多。

### 坑 6｜写文件报 `EROFS: read-only file system`

根因：**ego 的 node 进程工作目录是 `/`**，不是你在 shell 里 `cd` 的那个目录。所以 `./out.json` 一定失败。
处置：**输出路径一律用绝对路径**，用 `os.homedir()` 或 `os.tmpdir()` 拼。

```js
const os = await import("node:os");
const path = await import("node:path");
const OUT = path.join(os.homedir(), "out.json");   // ✅
// "./out.json"                                      // ❌ EROFS
```

### 坑 7｜`export DKA_XXX=1` 传不进去

根因：ego 的 node 进程**只带约 15 个白名单环境变量**（`HOME`、`PATH` 之类），你自定义的变量在 `process.env` 里是 `undefined`。
处置：**别用环境变量传参**。把配置写在脚本顶部的 `CONFIG` 对象里，改文件比改环境可靠。

```js
console.log(Object.keys(process.env).length);   // 实测约 15
console.log(process.env.MY_VAR);                // undefined
```

这两条合起来的意思是：**ego 里的 node 是个"半隔离"运行时**——它有文件系统和网络，但没有你的工作目录，也没有你的环境变量。把这两点写进脚本模板，能省掉每人半小时。

## 调用形状

heredoc 是实测最稳的写法（脚本从标准输入进）：

```bash
export PATH="$HOME/.local/bin:$PATH"
ego-browser nodejs <<'EOF'
const task = await taskSpace("my-job");
const page = task.page("p1");
await page.goto("https://example.com", { timeout: 40000 });
console.log(await page.title());
console.log(await page.snapshot());
await task.finish({ keep: [] });
EOF
```

要点：
- 同名 `taskSpace("my-job")` 会复用同一个 Space，中断后能接着干。
- `task.finish({ keep: [] })` 必须收尾，否则 Space 越积越多。
- `page.snapshot()` 是语义快照，比抓 DOM 省 token，先用它判断页面到了没有。
- `page.evaluate()` 里可以返回任意可序列化结构，一次取回多个字段，别来回往返。

## 验收（不验收等于没装）

| 检查 | 通过标准 |
|---|---|
| 运行时 | `ego-browser nodejs` 能打印 `node vXX` |
| 开页 | 拿得到 `title` 和 `url` |
| 快照 | 返回可读的语义结构，非空 |
| 截图 | `page.screenshot({path})` 落盘且能打开 |
| 登录态 | 打开一个需登录的站点，不弹登录框 |
| 收尾 | `task.finish` 之后不残留 Space |
