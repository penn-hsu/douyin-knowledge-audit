/**
 * 抖音收藏采集：在 ego-browser 的 nodejs 环境里跑。
 *
 *   export PATH="$HOME/.local/bin:$PATH"
 *   ego-browser nodejs < scripts/collect_favorites.js
 *
 * ⚠️ 两个必须知道的运行时事实（实测）：
 *   1) ego 的 node 进程 cwd 是 `/`，写相对路径会 EROFS。输出必须用绝对路径。
 *   2) 不继承自定义环境变量（只有约 15 个白名单变量，如 HOME）。
 *      所以参数写在下面 CONFIG 里，不要指望 export。
 */

const os = await import("node:os");
const path = await import("node:path");

const CONFIG = {
  space: "douyin-favorites",                          // Space 名，同名会复用
  maxItems: 800,                                      // 最多采集条数
  maxRounds: 40,                                      // 最多滚动轮数
  pageTotal: 0,                                       // 页面显示的总收藏数，填了才算覆盖率
  out: path.join(os.homedir(), "douyin-favorites.json"), // 必须是绝对路径
  headlessStay: true,                                 // 结束时不保留 Space
};

const SPACE = CONFIG.space;
const MAX_ITEMS = CONFIG.maxItems;
const MAX_ROUNDS = CONFIG.maxRounds;
const OUT = CONFIG.out;
const TOTAL = CONFIG.pageTotal;

if (!path.isAbsolute(OUT)) {
  throw new Error(`输出路径必须是绝对路径（当前 ${OUT}），ego 的 cwd 是 /，写入会 EROFS`);
}

const task = await taskSpace(SPACE);
const page = task.page("p1");

await page.goto("https://www.douyin.com/user/self?showTab=favorite_collection", {
  timeout: 45000,
});
await page.waitForLoadState("load");
await page.waitForTimeout(3500);

// 0. 登录态自检：没登录就先停，别空跑
const guest = await page.evaluate(() =>
  /扫码登录|登录后可查看/.test((document.body.innerText || "").slice(0, 800))
);
if (guest) {
  console.error("[stop] 未检测到登录态，请先在 ego lite 里登录或导入 Chrome 档案");
  await task.finish({ keep: [] });
  process.exit(2);
}

// 1. 卡片解析：作者与标题在 img[alt] 的「作者：描述」里
const collect = () =>
  page.evaluate(() =>
    [...document.querySelectorAll('li a[href*="/video/"]')].map((a) => {
      const li = a.closest("li");
      const img = li && li.querySelector("img");
      const alt = ((img && img.getAttribute("alt")) || "")
        .replace(/\s+/g, " ")
        .trim();
      const m = alt.match(/^([^：:]{1,20})[：:]\s*([\s\S]*)$/);
      const vid = ((a.getAttribute("href") || "").split("/video/")[1] || "").split("?")[0];
      const like = ((li && li.innerText) || "").match(/^\s*([\d.]+[万wW]?)/);
      return {
        id: vid,
        author: m ? m[1] : "",
        desc: (m ? m[2] : alt).slice(0, 220),
        like: like ? like[1] : "",
        url: "https://www.douyin.com/video/" + vid,
      };
    })
  );

// 2. 滚动容器是内层 route-scroll-container，不是 window
const scrollBottom = () =>
  page.evaluate(() => {
    const el = [...document.querySelectorAll("div")].find(
      (e) =>
        /route-scroll-container/.test((e.className || "").toString()) &&
        e.scrollHeight > e.clientHeight + 100
    );
    if (el) {
      el.scrollTop = el.scrollHeight;
      return el.scrollTop;
    }
    window.scrollTo(0, document.body.scrollHeight);
    return -1;
  });

// 3. 采集循环：去重 + 连续 3 轮无新增才判到底
const seen = new Map();
let rounds = 0;
let stall = 0;

while (rounds < MAX_ROUNDS && seen.size < MAX_ITEMS) {
  const before = seen.size;
  for (const it of await collect()) {
    if (it.id && !seen.has(it.id)) seen.set(it.id, it);
    if (seen.size >= MAX_ITEMS) break;
  }
  rounds += 1;
  stall = seen.size === before ? stall + 1 : 0;
  if (stall >= 3 || seen.size >= MAX_ITEMS || rounds >= MAX_ROUNDS) break;
  await scrollBottom();
  await page.waitForTimeout(1400);
}

const items = [...seen.values()];
if (!items.length) {
  console.error("[stop] 未采集到有效条目，请核对登录态、收藏页和页面结构；未写入成功报告");
  await task.finish({ keep: [] });
  process.exit(2);
}
const emptyAuthor = items.filter((i) => !i.author).length;

const fs = await import("node:fs/promises");
await fs.writeFile(
  OUT,
  JSON.stringify(
    {
      collectedAt: new Date().toISOString(),
      space: SPACE,
      rounds,
      stalled: stall >= 3,
      collected: items.length,
      pageTotal: TOTAL || null,
      coveragePercent: TOTAL ? +((items.length / TOTAL) * 100).toFixed(1) : null,
      emptyAuthor,
      items,
    },
    null,
    1
  ),
  "utf8"
);

console.log("[done]", {
  space: SPACE,
  rounds,
  collected: items.length,
  stopReason: stall >= 3 ? "stalled(3轮无新增)" : seen.size >= MAX_ITEMS ? "max-items" : "max-rounds",
  coverage: TOTAL ? ((items.length / TOTAL) * 100).toFixed(1) + "%" : "未提供 pageTotal",
  emptyAuthor,
  out: OUT,
});

if (emptyAuthor > items.length * 0.2) {
  console.warn("[warn] 作者字段空值率过高，可能页面结构变了，先抽样核对再往下走");
}

await task.finish({ keep: [] });
