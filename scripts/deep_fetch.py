#!/usr/bin/env python3
"""
深化抓取：从搜索结果URL列表，深入抓取每个招标详情页
提取：预算、招标时间、公司名、公司背景、历史采购供应商
"""

import urllib.request
import urllib.parse
import json
import time
import re
from datetime import datetime

# 监控的竞争公司
COMPETITORS = {
    "先导智能": "无锡先导智能装备股份有限公司",
    "海目星": "海目星激光科技集团股份有限公司",
    "赢合科技": "深圳市赢合科技股份有限公司",
    "联赢激光": "深圳市联赢激光股份有限公司"
}

# 搜索关键词
KEYWORDS = ["锂电池", "储能", "装配段", "锂电设备", "电池生产设备"]

def resolve_bing_url(bing_url):
    """解析 Bing 中转 URL，获取真实目标 URL"""
    try:
        req = urllib.request.Request(bing_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html",
        })
        resp = urllib.request.urlopen(req, timeout=10)
        final_url = resp.url
        resp.close()
        return final_url
    except Exception as e:
        return None

def extract_real_urls_from_bing(html):
    """从 Bing 搜索结果页提取真实目标 URL"""
    # Bing 搜索结果中的真实链接模式
    patterns = [
        # 指向真实目标的 URL
        r'href="(https?://(?!r\.bing\.com|th\.bing\.com|cn\.bing\.com)[^"?]+)"',
    ]
    urls = []
    for p in patterns:
        matches = re.findall(p, html)
        for m in matches:
            if any(x in m for x in ['招标', 'tender', 'caigou', 'zhaobiao', 'jdzx', 'ccgp', 'gov.cn']):
                urls.append(m)
    return list(set(urls))

def search_and_extract_real_urls(keyword, max_per_kw=10):
    """
    搜索关键词，直接从搜索结果页提取真实招标页面 URL
    返回真实 URL 列表
    """
    print(f"  [关键词: {keyword}]")
    encoded = urllib.parse.quote(keyword + " 招标公告")
    url = f"https://www.bing.com/search?q={encoded}&count=50"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }
    
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8', errors='replace')
        resp.close()
    except Exception as e:
        print(f"    搜索失败: {e}")
        return []
    
    real_urls = extract_real_urls_from_bing(html)
    print(f"    找到 {len(real_urls)} 个真实招标页面")
    return real_urls

def fetch_page_content(url, timeout=15):
    """抓取页面内容"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        content = resp.read().decode('utf-8', errors='replace')
        resp.close()
        return content
    except Exception as e:
        return None

def parse_tender_page(url, html):
    """从招标页面提取结构化信息"""
    result = {
        "url": url,
        "title": extract_title(html),
        "company": extract_company(html),
        "budget": extract_budget(html),
        "bid_deadline": extract_deadline(html),
        "publish_date": extract_publish_date(html),
        "description": extract_description(html),
        "contact": extract_contact(html),
        "found_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    return result

def extract_title(html):
    """提取标题"""
    patterns = [
        r'<title[^>]*>([^<]+)</title>',
        r'<h1[^>]*>([^<]+)</h1>',
        r'class="[^"]*title[^"]*"[^>]*>([^<]+)</',
    ]
    for p in patterns:
        m = re.search(p, html, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:200]
    return "未知"

def extract_company(html):
    """提取招标单位"""
    patterns = [
        r'招标人[：:]\s*([^<\n\r,，]{2,30})',
        r'采购人[：:]\s*([^<\n\r,，]{2,30})',
        r'([^\s\n\r]{5,20})(?:招标|采购)公告',
        r'单位名称[：:]\s*([^<\n\r]{2,30})',
    ]
    for p in patterns:
        m = re.search(p, html)
        if m:
            return m.group(1).strip()
    return "未知"

def extract_budget(html):
    """提取预算金额"""
    patterns = [
        r'预算[：:\s]*[￥$]?\s*([\d,，.]+)\s*(?:万|元|千万|百万)?\s*(?:人民币|元)?',
        r'采购预算[：:\s]*([\d,，.]+)\s*(?:万|元|千万)?',
        r'控制价[：:\s]*([\d,，.]+)\s*(?:万|元|千万)?',
        r'金额[：:\s]*([\d,，.]+)\s*(?:万|元|千万)?',
        r'([1-9]\d*[万元])',
    ]
    for p in patterns:
        m = re.search(p, html)
        if m:
            return m.group(0).strip()
    return "未知"

def extract_deadline(html):
    """提取投标截止时间"""
    patterns = [
        r'截止[时间：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?\s*\d{1,2}[时:]\d{1,2})',
        r'投标截止[时间：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)',
        r'开标[时间：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)',
        r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)',
    ]
    for p in patterns:
        m = re.search(p, html)
        if m:
            return m.group(1).strip().replace('年', '-').replace('月', '-').replace('日', '')
    return "未知"

def extract_publish_date(html):
    """提取发布时间"""
    patterns = [
        r'发布时间[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)',
        r'发布日期[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)',
        r'(\d{4}年\d{1,2}月\d{1,2}日)',
    ]
    for p in patterns:
        m = re.search(p, html)
        if m:
            return m.group(1).strip().replace('年', '-').replace('月', '-').replace('日', '')
    return "未知"

def extract_description(html):
    """提取项目描述（摘要前200字）"""
    patterns = [
        r'项目名称[：:]\s*([^<\n\r]{10,200})',
        r'项目概述[：:]\s*([^<\n\r]{10,200})',
        r'采购内容[：:]\s*([^<\n\r]{10,200})',
    ]
    for p in patterns:
        m = re.search(p, html)
        if m:
            return m.group(1).strip()[:200]
    # 通用摘要
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    return text[:200].strip()

def extract_contact(html):
    """提取联系方式"""
    patterns = [
        r'联系人[：:]\s*([^<\n\r,，]{2,20})',
        r'电话[：:]\s*(\d{3,4}[-\s]?\d{7,8})',
        r'联系方式[：:]\s*([^<\n\r]{5,50})',
    ]
    contacts = []
    for p in patterns:
        m = re.search(p, html)
        if m:
            contacts.append(m.group(0).strip())
    return ' | '.join(contacts) if contacts else "未知"

def main():
    """主流程：搜索 → 抓取详情 → 保存"""
    all_details = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    print(f"[{timestamp}] 开始深化抓取...")
    print(f"目标: 从真实招标页面提取详细信息\n")
    
    # Step 1: 搜索每个关键词，找到真实招标页面 URL
    real_urls_by_kw = {}
    for kw in KEYWORDS:
        urls = search_and_extract_real_urls(kw, max_per_kw=10)
        real_urls_by_kw[kw] = urls
        time.sleep(1)  # 避免过快
    
    # Step 2: 搜索竞争公司相关招标
    competitor_urls = {}
    for short_name in COMPETITORS.keys():
        urls = search_and_extract_real_urls(f"{short_name} 招标公告")
        competitor_urls[short_name] = urls
        time.sleep(1)
    
    # Step 3: 合并所有 URL 并去重
    all_real_urls = set()
    for urls in real_urls_by_kw.values():
        all_real_urls.update(urls)
    for urls in competitor_urls.values():
        all_real_urls.update(urls)
    
    print(f"\n共找到 {len(all_real_urls)} 个唯一招标页面")
    print("开始逐个抓取详情...\n")
    
    # Step 4: 逐个抓取详情
    for i, url in enumerate(sorted(all_real_urls), 1):
        print(f"[{i}/{len(all_real_urls)}] 抓取: {url[:60]}...")
        
        # 找出关联关键词
        keywords = []
        for kw, urls in real_urls_by_kw.items():
            if url in urls:
                keywords.append(kw)
        competitor = ""
        for short, urls in competitor_urls.items():
            if url in urls:
                competitor = short
        
        html = fetch_page_content(url)
        if html:
            detail = parse_tender_page(url, html)
            detail['keyword'] = ','.join(keywords)
            detail['competitor'] = competitor
            all_details.append(detail)
            print(f"  ✓ 标题: {detail['title'][:40]}")
            print(f"    公司: {detail['company']} | 预算: {detail['budget']}")
        else:
            print(f"  ✗ 抓取失败")
        
        time.sleep(0.5)
    
    # Step 5: 保存结果
    output_file = f"C:\\Users\\16323\\.openclaw\\workspace\\data\\bid_details_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_details, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*50}")
    print(f"深化抓取完成!")
    print(f"成功抓取 {len(all_details)} 个页面详情")
    print(f"结果保存: {output_file}")
    
    # 打印摘要
    if all_details:
        has_budget = sum(1 for d in all_details if d['budget'] != '未知')
        has_company = sum(1 for d in all_details if d['company'] != '未知')
        print(f"\n数据质量:")
        print(f"  有预算信息: {has_budget}/{len(all_details)}")
        print(f"  有公司名称: {has_company}/{len(all_details)}")

if __name__ == "__main__":
    main()
