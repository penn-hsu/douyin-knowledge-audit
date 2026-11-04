#!/usr/bin/env python3
"""主题打标 + 时间账 + 盲区扫描。

用法：
    python3 classify.py douyin-favorites.json -o out/
    python3 classify.py douyin-favorites.json --csv audit.csv

输入兼容两种：collect_favorites.js 产出的包装对象，或裸的条目数组。
输出：控制台摘要 +（可选）分类 CSV +（可选）JSON。
"""

import argparse
import csv
import json
import os
import sys

# 关键词表：宁可窄，不要宽。
# "工具""模型""运营"这类泛词会吃掉一切，让每类都虚高。
TOPICS = {
    "AI工具与Agent": [
        "agent", "智能体", "mcp", "工作流", "workflow", "claude", "codex", "cursor",
        "提示词", "prompt", "自动化", "n8n", "coze", "扣子", "数字员工", "vibe coding",
        "大模型", "api", "skill", "浏览器", "obsidian", "知识库", "ai实操", "新手学ai",
    ],
    "AI视频与图像": [
        "即梦", "可灵", "海螺", "seedance", "sora", "veo", "生图", "ai绘画", "绘画",
        "midjourney", "换脸", "图生视频", "文生视频", "一致性", "定妆", "分镜",
        "ai视频", "ai电影", "ai短剧", "漫剧", "ai动画", "出图", "ai建模", "混元3d",
        "3d建模", "ai创作",
    ],
    "剪辑与拍摄": [
        "剪辑", "运镜", "转场", "调色", "卡点", "特效", "音效", "配音", "字幕",
        "拍摄", "打光", "剪映", "达芬奇", "mv", "镜头", "后期", "抠像", "合成", "补帧",
    ],
    "音乐制作": [
        "suno", "编曲", "混音", "作曲", "歌词", "母带", "bpm", "edm", "配乐", "remix",
        "音乐制作", "dj培训",
    ],
    "内容运营IP": [
        "起号", "涨粉", "爆款", "选题", "口播", "流量", "算法", "私域", "文案", "人设",
        "矩阵", "变现", "带货", "直播", "冷启动", "完播", "封面", "评论区",
    ],
    "教培与课程": [
        "教培", "训练营", "课程", "招生", "学员", "知识付费", "校长", "家长", "考研",
        "体验课", "续费", "转介绍", "报名",
    ],
    "商业与管理": [
        "创业", "一号位", "组织", "管理", "复盘", "战略", "商业模式", "定价", "团队",
        "增长", "定位", "品牌",
    ],
}

# 盲区候选：这些方向如果一条都没有，是要单独说的
CRITICAL = {
    "音乐制作": "MV / 短片配乐只能现学现卖",
    "商业与管理": "做久了会只剩执行者视角，缺经营者视角",
    "教培与课程": "课程卖得动但交付不住",
}

MINUTES_PER_ITEM = 20
KEEP = 7


def load(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    if isinstance(d, dict):
        items = d.get("items", [])
        return items, d
    return d, {}


def tag(items):
    buckets = {k: [] for k in TOPICS}
    unmatched = []
    for it in items:
        text = f"{it.get('desc', '')} {it.get('author', '')}".lower()
        hit = [k for k, kws in TOPICS.items() if any(w.lower() in text for w in kws)]
        if hit:
            it["topics"] = hit
            for k in hit:
                buckets[k].append(it)
        else:
            unmatched.append(it)
    return buckets, unmatched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--csv", help="分类清单输出路径")
    ap.add_argument("-o", "--outdir", help="同时输出 JSON 汇总到该目录")
    ap.add_argument("--minutes", type=int, default=MINUTES_PER_ITEM)
    ap.add_argument("--show-unmatched", type=int, default=0, metavar="N",
                    help="抽样打印 N 条未命中，用来发现漏标、补关键词")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f"找不到输入文件：{args.input}")

    if args.minutes <= 0:
        ap.error("--minutes 必须大于 0")

    items, meta = load(args.input)
    if not items:
        sys.exit("输入里没有条目，先确认采集是否成功")

    buckets, unmatched = tag(items)
    uniq = {i.get("id") or i.get("url") or id(i) for b in buckets.values() for i in b}
    total = len(items)

    hours = len(uniq) * args.minutes / 60
    print(f"总条目        {total}")
    if meta.get("pageTotal"):
        print(f"页面总数      {meta['pageTotal']}（本次覆盖率 {len(items)/meta['pageTotal']:.1%}）")
    print(f"主题命中      {sum(len(v) for v in buckets.values())}（去重 {len(uniq)}）")
    print(f"未命中        {len(unmatched)}")
    print(f"名义学习时长  {hours:.1f} 小时（按每条 {args.minutes} 分钟）")
    print(f"可执行上限    {KEEP} 条 ≈ {KEEP * args.minutes} 分钟\n")

    print("## 主题分布")
    for k, v in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        bar = "█" * max(1, round(len(v) / max(1, total) * 40)) if v else ""
        print(f"{k:<14}{bar} {len(v)}")

    print("\n## 待核验方向（本次样本未命中，不代表能力缺失）")
    blanks = [k for k in CRITICAL if not buckets.get(k)]
    if blanks:
        for k in blanks:
            print(f"- {k}｜可结合项目目标检查：{CRITICAL[k]}")
    else:
        print("- 未发现关键方向空缺")

    print("\n## 结构判断")
    counts = sorted((len(v) for v in buckets.values()), reverse=True)
    if counts and sum(counts[:3]) / max(1, sum(counts)) > 0.7:
        print("- 前三类占七成以上：样本主题较集中，需结合具体类别、采集覆盖率和项目目标判断")
        print("- 先检查未命中样本与关键词漏标，再决定是否补充学习方向")
    elif sum(counts[:3]) < sum(counts) * 0.4:
        print("- 分布较散：先定一条主线，别同时开五条")

    if args.show_unmatched:
        print(f"\n## 未命中抽样（看有没有明显该进类却没进的）")
        for it in unmatched[: args.show_unmatched]:
            print(f"- {(it.get('author') or '')[:10]:<10} | {(it.get('desc') or '')[:56]}")

    if args.csv:
        os.makedirs(os.path.dirname(args.csv) or ".", exist_ok=True)
        with open(args.csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["主题", "作者", "点赞", "标题", "链接"])
            for k, v in buckets.items():
                for it in v:
                    w.writerow([k, it.get("author", ""), it.get("like", ""),
                                (it.get("desc") or "").replace("\n", " "), it.get("url", "")])
        print(f"\nCSV 已写入 {args.csv}")

    if args.outdir:
        os.makedirs(args.outdir, exist_ok=True)
        summary = {
            "total": total,
            "unique_hit": len(uniq),
            "unmatched": len(unmatched),
            "nominal_hours": round(hours, 1),
            "keep": KEEP,
            "buckets": {k: len(v) for k, v in buckets.items()},
            "blind_spots": blanks,
            "coverage": total / meta["pageTotal"] if isinstance(meta.get("pageTotal"), (int, float)) and meta["pageTotal"] > 0 else None,
            "coverage_note": "仅为采集样本覆盖率；未命中主题不代表能力缺失",
        }
        p = os.path.join(args.outdir, "audit-summary.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=1)
        print(f"汇总已写入 {p}")


if __name__ == "__main__":
    main()
