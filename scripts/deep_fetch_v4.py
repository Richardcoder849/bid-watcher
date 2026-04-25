#!/usr/bin/env python3
"""
深化抓取 v4：多平台 + 精准关键词 + 竞争公司招标
"""
import urllib.request
import urllib.parse
import json
import time
import re
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

def fetch(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=timeout)
        c = resp.read().decode('utf-8', errors='replace')
        resp.close()
        return c
    except:
        return None

def extract(text, patterns):
    for p in patterns:
        m = re.search(p, text)
        if m:
            val = m.group(1).strip()
            if val:
                return val[:100]
    return "未知"

def parse_tender(url, html):
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    
    return {
        "url": url,
        "title": extract(html, [r'<title[^>]*>([^<]+)</title>']),
        "company": extract(text, [
            r'招标[人方][：:]\s*([^\s，,。]{2,40})',
            r'采购[人方][：:]\s*([^\s，,。]{2,40})',
            r'([^\s，,。]{5,30})(?:招标|采购)公告',
        ]),
        "budget": extract(text, [
            r'预算[：:]\s*[￥$]?\s*([\d,，.]+\s*(?:万|元|千万|百万)?)',
            r'采购预算[：:]\s*([\d,，.]+\s*(?:万|元|千万)?)',
            r'最高限价[：:]\s*([\d,，.]+\s*(?:万|元)?)',
            r'(?:项目)?金额[：:]\s*([\d,，.]+\s*(?:万|元)?)',
        ]),
        "bid_deadline": extract(text, [
            r'(?:截止?|截稿)[^0-9]*(\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}[日]?)',
            r'投标截止[^0-9]*(\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}[日]?)',
            r'开标[^0-9]*(\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}[日]?)',
        ]),
        "publish_date": extract(text, [
            r'发布时间[：:]\s*(\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}[日]?)',
            r'发布日期[：:]\s*(\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}[日]?)',
        ]),
        "contact": extract(text, [
            r'联系人[：:]\s*([^\s，,]{2,20})',
            r'电话[：:]\s*([\d\-\s]{7,20})',
        ]),
        "found_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

# ============================================================
# 平台配置
# ============================================================
PLATFORMS = {
    # 中国政府采购网
    "ccgp": {
        "search": lambda kw, page: (
            f"https://search.ccgp.gov.cn/bxsearch?searchtype=1&keyword={urllib.parse.quote(kw)}"
            f"&page_index={page}"
        ),
        "links_pattern": r'(http://www\.ccgp\.gov\.cn/cggg/[^\s"]+\.htm)',
        "max_pages": 3,
        "delay": 0.5
    },
}

# 精准关键词（与行业相关）
PRECISE_KEYWORDS = [
    "锂电池生产设备 招标",
    "储能系统设备 招标",
    "电池制造设备 招标",
    "锂电产线设备 招标",
    "储能电池系统 招标",
    "动力电池设备 招标",
    "电池生产线上 招标",
]

# 竞争公司招标公告
COMPETITOR_TENDER_KEYWORDS = [
    "无锡先导智能 招标公告",
    "海目星激光 招标公告",
    "赢合科技 招标公告",
    "联赢激光 招标公告",
]

def search_platform(name, config, keywords, max_links_per_kw=5):
    """搜索单个平台"""
    all_links = []
    
    for kw in keywords:
        print(f"\n  [{name}] {kw}")
        
        for page in range(1, config["max_pages"] + 1):
            url = config["search"](kw, page)
            html = fetch(url)
            
            if not html:
                continue
            
            # 提取链接
            links = re.findall(config["links_pattern"], html)
            links = list(set(links))
            
            if page == 1:
                print(f"    第1页: +{len(links)} 条")
            else:
                print(f"    第{page}页: +{len(links)} 条")
            
            # 只取前几个
            for l in links[:max_links_per_kw]:
                all_links.append((l, kw))
            
            time.sleep(config["delay"])
    
    return all_links

def fetch_and_parse(url):
    """抓取并解析"""
    html = fetch(url)
    if not html or len(html) < 500:
        return None
    try:
        return parse_tender(url, html)
    except:
        return None

def main():
    all_details = []
    seen_urls = set()
    all_link_tuples = []  # (url, kw) tuples
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 深化抓取 v4 - 多平台精准抓取\n")
    
    # Step 1: 精准关键词搜索各平台
    for name, config in PLATFORMS.items():
        print(f"\n{'='*50}")
        print(f"平台: {name.upper()}")
        links = search_platform(name, config, PRECISE_KEYWORDS, max_links_per_kw=5)
        
        new_links = [(url, kw) for url, kw in links if url not in seen_urls]
        seen_urls.update(url for url, _ in links)
        all_link_tuples.extend(new_links)
        print(f"  新增链接: {len(new_links)} 条")
    
    # Step 2: 竞争公司招标公告
    print(f"\n{'='*50}")
    print("竞争公司招标公告搜索")
    comp_links = search_platform("ccgp", PLATFORMS["ccgp"], COMPETITOR_TENDER_KEYWORDS, max_links_per_kw=5)
    new_comp = [(url, kw) for url, kw in comp_links if url not in seen_urls]
    seen_urls.update(url for url, _ in comp_links)
    all_link_tuples.extend(new_comp)
    print(f"  新增链接: {len(new_comp)} 条")
    
    unique_links = all_link_tuples
    print(f"\n{'='*50}")
    print(f"共 {len(unique_links)} 个唯一页面待抓取")
    
    # Step 3: 抓取详情
    print("\n开始抓取详情...\n")
    
    for i, (url, kw) in enumerate(unique_links, 1):
        short_url = '/'.join(url.split('/')[-2:]) if '/' in url else url[:40]
        print(f"[{i}/{len(unique_links)}] {short_url}")
        
        detail = fetch_and_parse(url)
        if detail:
            detail['keyword'] = kw
            all_details.append(detail)
            
            title = detail['title'][:35] if detail['title'] != '未知' else '无标题'
            budget = detail['budget'][:15] if detail['budget'] != '未知' else '无预算'
            print(f"  [OK] {title}")
            print(f"       预算:{budget}")
        else:
            print(f"  [FAIL]")
        
        time.sleep(0.3)
    
    # Step 4: 保存
    out = f"C:\\Users\\16323\\.openclaw\\workspace\\data\\bid_details_v4_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(all_details, f, ensure_ascii=False, indent=2)
    
    # 统计
    has_budget = sum(1 for d in all_details if d['budget'] != '未知')
    has_company = sum(1 for d in all_details if d['company'] != '未知')
    has_deadline = sum(1 for d in all_details if d['bid_deadline'] != '未知')
    
    print(f"\n{'='*50}")
    print(f"完成! 抓取 {len(all_details)}/{len(unique_links)} 个页面")
    print(f"保存: {out}")
    print(f"\n数据质量:")
    print(f"  有预算: {has_budget}/{len(all_details)}")
    print(f"  有公司: {has_company}/{len(all_details)}")
    print(f"  有截止: {has_deadline}/{len(all_details)}")
    
    # 保存摘要供查看
    summary_file = f"C:\\Users\\16323\\.openclaw\\workspace\\data\\bid_summary_v4_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"深化抓取 v4 摘要 - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"{'='*50}\n\n")
        for d in all_details:
            f.write(f"标题: {d.get('title', '未知')}\n")
            f.write(f"单位: {d.get('company', '未知')}\n")
            f.write(f"预算: {d.get('budget', '未知')}\n")
            f.write(f"截止: {d.get('bid_deadline', '未知')}\n")
            f.write(f"链接: {d.get('url', '')}\n")
            f.write(f"关键词: {d.get('keyword', '')}\n")
            f.write(f"{'-'*30}\n")
    
    print(f"\n摘要: {summary_file}")

if __name__ == "__main__":
    main()
