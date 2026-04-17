#!/usr/bin/env python3
"""
统计微信群每日消息数量分布
用法: python scripts/daily_stats.py --start-date 2026-03-01 --end-date 2026-04-17 --group "AI实践群"
"""

import argparse
import datetime
import json
import sys
import os

# 添加父目录到路径
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _ROOT_DIR)

from digest import _do_extract, load_config, resolve_group


def generate_date_range(start_date, end_date):
    """生成日期范围列表"""
    dates = []
    current = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += datetime.timedelta(days=1)
    return dates


def main():
    parser = argparse.ArgumentParser(description="统计微信群每日消息数量")
    parser.add_argument("--start-date", default="2026-03-01", help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end-date", default=datetime.date.today().strftime("%Y-%m-%d"), help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--group", default="AI实践群", help="群名称")
    parser.add_argument("--json", action="store_true", help="输出JSON格式")
    args = parser.parse_args()

    dates = generate_date_range(args.start_date, args.end_date)
    
    stats = []
    total_messages = 0
    active_days = 0
    
    print(f"正在统计群「{args.group}」从 {args.start_date} 到 {args.end_date} 的消息分布...\n", file=sys.stderr)
    
    for date_str in dates:
        try:
            messages, group_username = _do_extract(args.group, date_str, compact=True, no_cache=False)
            count = len(messages)
            total_messages += count
            if count > 0:
                active_days += 1
            stats.append({
                "date": date_str,
                "count": count,
                "group_username": group_username
            })
            print(f"{date_str}: {count} 条消息", file=sys.stderr)
        except Exception as e:
            stats.append({
                "date": date_str,
                "count": 0,
                "error": str(e)
            })
            print(f"{date_str}: 获取失败 - {e}", file=sys.stderr)
    
    # 计算统计信息
    counts = [s["count"] for s in stats if "error" not in s]
    avg_per_day = total_messages / len(dates) if dates else 0
    avg_active_day = total_messages / active_days if active_days > 0 else 0
    max_day = max(stats, key=lambda x: x["count"]) if stats else None
    min_day = min(stats, key=lambda x: x["count"]) if stats else None
    
    # 按消息数分组统计
    ranges = {
        "0条": 0,
        "1-10条": 0,
        "11-50条": 0,
        "51-100条": 0,
        "101-200条": 0,
        "200条+": 0
    }
    for s in stats:
        c = s["count"]
        if c == 0:
            ranges["0条"] += 1
        elif c <= 10:
            ranges["1-10条"] += 1
        elif c <= 50:
            ranges["11-50条"] += 1
        elif c <= 100:
            ranges["51-100条"] += 1
        elif c <= 200:
            ranges["101-200条"] += 1
        else:
            ranges["200条+"] += 1
    
    result = {
        "group": args.group,
        "date_range": f"{args.start_date} 至 {args.end_date}",
        "total_days": len(dates),
        "active_days": active_days,
        "total_messages": total_messages,
        "avg_per_day": round(avg_per_day, 1),
        "avg_active_day": round(avg_active_day, 1),
        "max_day": max_day,
        "min_day": min_day,
        "distribution": ranges,
        "daily_stats": stats
    }
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 打印可视化报告
        print("\n" + "="*60)
        print(f"群「{args.group}」消息统计报告")
        print("="*60)
        print(f"统计周期: {args.start_date} 至 {args.end_date} ({len(dates)} 天)")
        print(f"总消息数: {total_messages} 条")
        print(f"活跃天数: {active_days} 天 ({active_days/len(dates)*100:.1f}%)")
        print(f"日均消息: {avg_per_day:.1f} 条")
        print(f"活跃日平均: {avg_active_day:.1f} 条")
        if max_day:
            print(f"峰值日期: {max_day['date']} ({max_day['count']} 条)")
        print("-"*60)
        print("消息数量分布:")
        for range_name, days in ranges.items():
            bar = "#" * int(days / len(dates) * 40)
            print(f"  {range_name:10s}: {days:3d} 天 {bar}")
        print("-"*60)
        print("每日详情:")
        for s in stats:
            bar = "#" * min(int(s["count"] / 10), 30)
            print(f"  {s['date']}: {s['count']:4d} 条 {bar}")


if __name__ == "__main__":
    main()
