# 页面配方：抖音收藏页怎么读

抖音是 SPA，且做了大量虚拟化与节流。**照普通网页的抓法，你只会拿到首屏 20 条。**

## 三个必须先摸清的事实

### 1｜滚动容器不是 window

收藏列表在一个内层滚动容器里。滚 `window` 无效，页面纹丝不动。

```js
// 先探测：谁真的能滚
const cands = [...document.querySelectorAll("div")].filter(el => {
  const s = getComputedStyle(el);
  return /(auto|scroll)/.test(s.overflowY) && el.scrollHeight > el.clientHeight + 200;
}).map(el => ({
  cls: (el.className || "").toString().slice(0, 60),
  scrollHeight: el.scrollHeight,
  clientHeight: el.clientHeight,
}));
```

收藏页的容器类名含 `route-scroll-container`。写法：

```js
await page.evaluate(() => {
  const el = [...document.querySelectorAll("div")].find(e =>
    /route-scroll-container/.test((e.className || "").toString()) &&
    e.scrollHeight > e.clientHeight + 100);
  if (el) el.scrollTop = el.scrollHeight;
});
```

### 2｜字段藏在 `img[alt]` 里

卡片可见文本只有点赞数之类的碎片。**作者和标题在图片的 alt 上，格式是「作者：描述」。**

```js
const items = [...document.querySelectorAll('li a[href*="/video/"]')].map(a => {
  const li = a.closest("li");
  const alt = (li.querySelector("img")?.getAttribute("alt") || "").replace(/\s+/g, " ").trim();
  const m = alt.match(/^([^：:]{1,20})[：:]\s*([\s\S]*)$/);
  const vid = (a.getAttribute("href") || "").split("/video/")[1]?.split("?")[0];
  return {
    id: vid,
    author: m ? m[1] : "",
    desc: (m ? m[2] : alt).slice(0, 220),
    url: "https://www.douyin.com/video/" + vid,
  };
});
```

不要用 `innerText` 抓标题——它拿到的是被截断的显示文本，且随视口变化。

### 3｜数字有两套

| 位置 | 数字性质 |
|---|---|
| 收藏列表页 | **缓存值**，可能落后数小时到数天 |
| 视频详情页 | 实时值 |

需要对外引用数字时，必须回详情页复核。我们实测遇到过一次：列表 3121，详情页 3186，差 65。

## 采集循环（去重 + 停滞判定）

```js
const seen = new Map();
let stall = 0;
while (seen.size < 800) {
  for (const it of await collect()) {
    if (it.id && !seen.has(it.id)) seen.set(it.id, it);
  }
  const before = seen.size;
  await scrollBottom();
  await page.waitForTimeout(1400);        // 低于 1.2s 容易触发节流
  stall = seen.size === before ? stall + 1 : 0;
  if (stall >= 3) break;                  // 连续 3 轮无新增 = 到底
}
```

三条纪律：
- **单轮滚动间隔 ≥1.2 秒**。更快会被节流，看起来在滚其实没加载。
- **连续 3 轮无新增才停**。停得太早会漏，停得太晚浪费时间。
- **设上限**（如 800）。收藏上万时不要试图一次全拉，那是跟自己过不去。

## 覆盖率必须如实报

抓完算一下：`已抓 / 页面显示的总数`。我们曾拿到 718 / 3095 ≈ 23%。

**23% 是高置信切片，不是全库结论。** 这句话必须写进交付，否则下游所有判断都站不住。

## 其他可复用入口

| 目标 | 路径 |
|---|---|
| 收藏 / 作品 | `https://www.douyin.com/user/self?showTab=favorite_collection` |
| 单条视频 | `https://www.douyin.com/video/<id>` |
| 创作者中心 | `https://creator.douyin.com/creator-micro/home` |
| 评论管理 | `https://creator.douyin.com/creator-micro/interactive/comment` |
| 上传发布 | `https://creator.douyin.com/creator-micro/content/upload` |

详情页可稳定取值的属性：`[data-e2e="video-player-digg"]`（点赞）、`[data-e2e="video-player-collect"]`（收藏）、`[data-e2e="detail-video-info"]`（简介区）。
