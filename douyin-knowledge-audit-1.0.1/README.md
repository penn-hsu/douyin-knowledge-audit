# 抖音知识盘查 1.0

把「我收藏了三千条但从来没学」变成一份能执行的判断：**留哪 7 条、砍掉什么、哪些方向一条都没收藏。**

## 它解决的问题

收藏夹不是学习计划，是焦虑缓冲池。

- 224 条去重候选 × 20 分钟 ≈ **75 小时**
- 三千条收藏 ≈ **一千小时**

算完这笔账，问题就换了：不是"怎么学完"，是"**从里面挑出一条能立刻接上现有项目的最小路径**"。

## 前置

| 需要 | 说明 |
|---|---|
| ego lite（`ego-browser`） | 提供继承真实登录态的浏览器能力。**需自行安装**，本包不含也不分发其二进制 |
| 已登录的抖音账号 | 登录态由 ego lite 从你的浏览器档案继承，本包不保存任何凭证 |
| Python 3.9+ | 只给 `scripts/classify.py` 用，无第三方依赖 |

## 四步跑完

```bash
# 1. 采集：先打开脚本顶部 CONFIG，把 pageTotal 改成你页面上显示的收藏总数
export PATH="$HOME/.local/bin:$PATH"
ego-browser nodejs < scripts/collect_favorites.js

# 2. 打标 + 算时间账 + 扫盲区
python3 scripts/classify.py ~/douyin-favorites.json --csv ./audit.csv --show-unmatched 8
```

> 参数写在 `CONFIG` 里，**不走环境变量**——ego 的 node 进程不继承自定义变量，且工作目录是 `/`，输出必须绝对路径。这两条已在 `references/ego-setup.md` 坑 6、坑 7 里说明。

3. 读 `references/audit-method.md`，按三条原则把命中清单砍到 7 条。
4. 读 `references/validation.md`，逐条打开核对，写清覆盖率。

## 目录

| 文件 | 作用 |
|---|---|
| `SKILL.md` | 入口与边界 |
| `references/ego-setup.md` | ego 接入三步 + 五个实测坑 |
| `references/dom-recipes.md` | 抖音收藏页怎么读（滚动容器、字段、数字两套） |
| `references/audit-method.md` | 三千条砍到七条的五个动作 |
| `references/write-ops.md` | 点赞 / 回评 / 发视频的三级纪律 |
| `references/validation.md` | 验收标准与禁止出现的表述 |
| `scripts/collect_favorites.js` | 采集循环（去重 + 停滞判定 + 覆盖率） |
| `scripts/classify.py` | 主题打标、时间账、盲区扫描、CSV 导出 |

## 实测范围（不夸大）

- 采集、解析、滚动容器、打标、时间账：**在真实账号 718 条样本上实跑通过**
- 样本覆盖率 **718 / 3095 ≈ 23%**，是全库的切片，不是全库
- 写操作边界另行实测：点赞可双向验证并还原；评论回复框在位（未提交）；上传页有真实 `input[type=file]`
- **未验证**：800 条以上连续采集、他人账号、不同账号的关键词表适配

## 许可证

MIT。ego lite 为独立 MIT 项目（Copyright (c) 2026 CitroLabs），本包不分发其代码。
