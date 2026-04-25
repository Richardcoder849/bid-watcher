#!/usr/bin/env python3
"""
深化抓取 v2：直接从 Bing 搜索结果中提取真实目标 URL 并逐个抓取
"""

import urllib.request
import urllib.parse
import json
import time
import re
from datetime import datetime

KEYWORDS = ["锂电池 招标公告", "储能 招标公告", "装配段 招标公告", "锂电设备 招标公告", "电池生产设备 招标公告"]
COMPETITORS = ["无锡先导智能 招标公告", "海目星激光 招标公告", "赢合科技 招标公告", "联赢激光 招标公告"]

def fetch_bing_search_page(query, count=20):
    """获取 Bing 搜索结果页 HTML"""
    encoded = urllib.parse.quote(query)
    url = f"https://www.bing.com/search?q={encoded}&count={count}&first=0"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8', errors='replace')
        resp.close()
        return html
    except Exception as e:
        print(f"  [!] 搜索失败: {e}")
        return None

def extract_links_v2(html):
    """从 Bing 搜索页提取所有链接"""
    # 匹配形式: href="/labs/acadia/api/LabInfo?G...
    # 以及形式: href="http://www.xxx.com/..."
    pattern = r'href="([^"]+)"'
    matches = re.findall(pattern, html)
    
    real_urls = []
    seen = set()
    
    for href in matches:
        # 跳过 Bing 内部链接
        if '/labs/' in href or '/api/' in href or href.startswith('/search'):
            continue
        if 'bing.com' in href and not href.startswith('http'):
            continue
        
        # 清理 URL
        url = href.split('?')[0].split('#')[0]
        
        # 去重且必须是 http/https 开头
        if url not in seen and url.startswith('http'):
            seen.add(url)
            real_urls.append(url)
    
    return real_urls

def resolve_redirect(url, timeout=10):
    """跟随重定向获取最终 URL"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html",
        })
        resp = urllib.request.urlopen(req, timeout=timeout)
        final_url = resp.url
        resp.close()
        return final_url
    except:
        return url

def fetch_page(url, timeout=15):
    """抓取页面内容"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        resp = urllib.request.urlopen(req, timeout=timeout)
        content = resp.read().decode('utf-8', errors='replace')
        resp.close()
        return content
    except:
        return None

def parse_tender_info(url, html):
    """解析招标页面信息"""
    # 清理 HTML
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    
    result = {
        "url": url,
        "title": extract_field(html, [r'<title[^>]*>([^<]+)</title>']),
        "company": extract_field(text, [
            r'招标人[：:]\s*([^\s，,，。]{2,30})',
            r'采购人[：:]\s*([^\s，,，。]{2,30})',
            r'([^\s，,，。]{5,20})(?:招标|采购)公告',
        ]),
        "budget": extract_field(text, [
            r'预算[：:]\s*[￥$]?\s*([\d,，.]+\s*(?:万|元|千万|百万)?)',
            r'采购预算[：:]\s*([\d,，.]+\s*(?:万|元|千万)?)',
            r'金额[：:]\s*([\d,，.]+\s*(?:万|元|千万)?)',
        ]),
        "bid_deadline": extract_field(text, [
            r'(?:截止|截稿)[^0-9]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)',
            r'投标截止[^0-9]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)',
        ]),
        "publish_date": extract_field(text, [
            r'发布时间[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)',
            r'发布日期[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)',
        ]),
        "contact": extract_field(text, [
            r'联系人[：:]\s*([^\s，,，]{2,20})',
            r'电话[：:]\s*([\d\-]{7,20})',
        ]),
        "description": text[:300].strip(),
    }
    return result

def extract_field(text, patterns):
    """用多个模式尝试提取字段"""
    for p in patterns:
        m = re.search(p, text)
        if m:
            val = m.group(1).strip()
            if val and val != '未知':
                return val[:100]
    return "未知"

def main():
    all_details = []
    all_urls = set()
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始深化抓取 v2\n")
    
    # 搜索关键词 + 竞争公司
    queries = KEYWORDS + COMPETITORS
    
    for query in queries:
        print(f"[搜索] {query}")
        html = fetch_bing_search_page(query, count=20)
        if html:
            links = extract_links_v2(html)
            print(f"  → 找到 {len(links)} 个链接")
            
            # 只保留可能是招标页面的 URL（政采云、政府网站、行业平台）
            tender_links = [l for l in links if any(x in l.lower() for x in [
                'zhaobiao', 'caigou', 'ccgp', 'gov.cn', 'tender', 
                'bid', 'jdzx', '政采', '招标', '采购', 'zf.gov'
            ])]
            
            print(f"  → 过滤后 {len(tender_links)} 个招标相关链接")
            
            for url in tender_links[:8]:  # 每个词最多8个
                all_urls.add(url)
        
        time.sleep(1)
    
    print(f"\n共 {len(all_urls)} 个待抓取页面\n")
    
    # 逐个抓取
    for i, url in enumerate(sorted(all_urls), 1):
        print(f"[{i}/{len(all_urls)}] {url[:70]}...")
        
        html = fetch_page(url)
        if html:
            info = parse_tender_info(url, html)
            all_details.append(info)
            print(f"  ✓ {info['title'][:40]}")
            print(f"    预算:{info['budget']} | 公司:{info['company']}")
        else:
            print(f"  ✗ 失败")
        
        time.sleep(0.3)
    
    # 保存
    out_file = f"C:\\Users\\16323\\.openclaw\\workspace\\data\\bid_details_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(all_details, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*50}")
    print(f"完成! 成功抓取 {len(all_details)}/{len(all_urls)} 个页面")
    print(f"保存: {out_file}")
    
    # 统计
    has_budget = sum(1 for d in all_details if d['budget'] != '未知')
    has_company = sum(1 for d in all_details if d['company'] != '未知')
    print(f"\n数据质量: 有预算{has_budget}条, 有公司{has_company}条")

if __name__ == "__main__":
    main()
