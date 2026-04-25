#!/usr/bin/env python3
"""
深化抓取 v5：基于CSV文件中的真实来源平台精准抓取
来源：北极星能源网(bjx.com.cn)、新能源网等
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
    except Exception as e:
        return None

def extract(text, patterns):
    for p in patterns:
        m = re.search(p, text, re.DOTALL)
        if m:
            val = m.group(1).strip()
            if val:
                return val[:150]
    return "未知"

def parse_tender_detail(url, source=""):
    """解析招标详情页"""
    html = fetch(url)
    if not html or len(html) < 500:
        return None
    
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    
    result = {
        "url": url,
        "source": source,
        "title": extract(html, [r'<title[^>]*>([^<]+)</title>']),
        "company": extract(text, [
            r'招标[人方][：:]\s*([^\s，,。]{2,40})',
            r'采购[人方][：:]\s*([^\s，,。]{2,40})',
            r'([^\s，,。]{5,30})(?:招标|采购)公告',
        ]),
        "budget": extract(text, [
            r'预算[：:]\s*[￥$]?\s*([\d,，.]+\s*(?:万|元|千万|百万|GWh|MWh|kWh)?)',
            r'采购预算[：:]\s*([\d,，.]+\s*(?:万|元|千万)?)',
            r'金额[：:]\s*([\d,，.]+\s*(?:万|元|千万)?)',
            r'([\d,，.]+\s*(?:亿|万|元))(?:人民币)?',
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
            r'联系方式[：:]\s*([^\n\r]{5,50})',
        ]),
        "found_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    return result

def search_bjx(keyword, max_pages=3):
    """搜索北极星能源网"""
    encoded = urllib.parse.quote(keyword)
    all_links = []
    
    for page in range(1, max_pages + 1):
        url = f"https://www.bjx.com.cn/search/?query={encoded}&page={page}"
        html = fetch(url)
        
        if not html:
            continue
        
        # 提取新闻/公告链接
        links = re.findall(r'href="(https?://[^"?]*bjx\.com\.cn[^"?]*)"', html)
        links = list(set(links))
        
        # 过滤：只要内容页
        content_links = [l for l in links if any(x in l for x in ['.shtml', '/news/', '/mnews/', '/article'])]
        all_links.extend(content_links)
        
        print(f"  第{page}页: +{len(content_links)} 条")
        time.sleep(0.5)
    
    return all_links

def fetch_from_url(url, source=""):
    """直接抓取URL页面"""
    html = fetch(url)
    if not html or len(html) < 500:
        return None
    return parse_tender_detail(url, source)

def main():
    all_details = []
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 深化抓取 v5 - 精准来源\n")
    
    # 来源1: 直接从CSV文件中的已有链接抓取详情
    csv_links = [
        ("https://m.bjx.com.cn/mnews/20231218/1350560.shtml", "北极星能源网"),
        ("https://www.escn.com.cn/news/show-2070171.html", "能源界网"),
        ("https://m.bjx.com.cn/mnews/20250214/1427048.html", "北极星能源网"),
        ("https://eraes.com.cn/newsinfo/9000663.html", "新能源网"),
        ("https://m.bjx.com.cn/mnews/20231007/1335127.html", "北极星能源网"),
        ("https://m.bjx.com.cn/mnews/20250218/1427649.html", "北极星能源网"),
        ("https://www.cpem.org.cn/list35/117357.html", "电力设备网"),
        ("https://finance.sina.com.cn/roll/2026-02-25/doc-inhnzrtk5110032.shtml", "新浪财经"),
        ("https://www.inengyuan.com/chuneng/12982.html", "能源界"),
        ("https://finance.sina.com.cn/roll/2025-02-14/doc-inekmitf4256466.shtml", "新浪财经"),
    ]
    
    print(f"【来源1】从CSV已有链接抓取 ({len(csv_links)}条)\n")
    for i, (url, src) in enumerate(csv_links, 1):
        short = url.split('/')[-1][:40]
        print(f"[{i}/{len(csv_links)}] {short}")
        
        detail = fetch_from_url(url, src)
        if detail:
            all_details.append(detail)
            title = detail['title'][:40] if detail['title'] != '未知' else '无标题'
            budget = detail['budget'][:15] if detail['budget'] != '未知' else '无预算'
            print(f"  OK | {title}")
            print(f"      预算:{budget} | 截止:{detail['bid_deadline']}")
        else:
            print(f"  FAIL")
        time.sleep(0.3)
    
    # 来源2: 关键词搜索北极星新线索
    print(f"\n{'='*50}")
    print("【来源2】关键词搜索新线索\n")
    
    keywords = [
        "储能系统设备 招标采购",
        "锂电池PACK 招标公告",
        "储能电池 招标采购",
        "电池生产线设备 招标",
    ]
    
    seen_urls = set(d['url'] for d in all_details)
    new_links_total = []
    
    for kw in keywords:
        print(f"\n[搜索] {kw}")
        links = search_bjx(kw, max_pages=2)
        new_links = [l for l in links if l not in seen_urls and l not in new_links_total]
        new_links_total.extend(new_links)
        print(f"  新增: {len(new_links)} 条")
    
    print(f"\n共 {len(new_links_total)} 个新链接，开始抓取...\n")
    
    for i, url in enumerate(new_links_total, 1):
        short = url.split('/')[-1][:40]
        print(f"[{i}/{len(new_links_total)}] {short}")
        
        detail = fetch_from_url(url, "北极星能源网-搜索")
        if detail:
            all_details.append(detail)
            title = detail['title'][:40] if detail['title'] != '未知' else '无标题'
            print(f"  OK | {title}")
        else:
            print(f"  FAIL")
        time.sleep(0.3)
    
    # 保存
    out = f"C:\\Users\\16323\\.openclaw\\workspace\\data\\bid_details_v5_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(all_details, f, ensure_ascii=False, indent=2)
    
    # 统计
    has_budget = sum(1 for d in all_details if d.get('budget', '未知') != '未知')
    has_company = sum(1 for d in all_details if d.get('company', '未知') != '未知')
    has_deadline = sum(1 for d in all_details if d.get('bid_deadline', '未知') != '未知')
    has_contact = sum(1 for d in all_details if d.get('contact', '未知') != '未知')
    
    print(f"\n{'='*50}")
    print(f"完成! 共 {len(all_details)} 条")
    print(f"保存: {out}")
    print(f"\n数据质量:")
    print(f"  有预算: {has_budget}/{len(all_details)}")
    print(f"  有公司: {has_company}/{len(all_details)}")
    print(f"  有截止: {has_deadline}/{len(all_details)}")
    print(f"  有联系: {has_contact}/{len(all_details)}")
    
    # 按来源统计
    from collections import Counter
    sources = Counter(d.get('source', '') for d in all_details)
    print(f"\n来源分布:")
    for s, c in sources.most_common():
        print(f"  {s}: {c}条")

if __name__ == "__main__":
    main()
