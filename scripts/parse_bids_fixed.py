#!/usr/bin/env python3
"""
修复后的 parse_bids.py - 直接访问 CCGP 招标平台
"""
import urllib.request
import urllib.parse
import json
import time
import re
import ssl
from datetime import datetime

# 忽略 SSL 证书
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "http://search.ccgp.gov.cn/",
}

KEYWORDS = ["锂电池", "储能", "锂电设备", "电池生产设备"]
COMPETITORS = {
    "先导智能": "无锡先导智能装备股份有限公司",
    "海目星": "海目星激光科技集团",
    "赢合科技": "深圳市赢合科技",
    "联赢激光": "深圳市联赢激光",
}

def fetch_ccgp(keyword, max_pages=2):
    """直接抓取 CCGP 搜索结果"""
    encoded = urllib.parse.quote(keyword)
    results = []
    
    for page in range(1, max_pages + 1):
        url = (f"http://search.ccgp.gov.cn/bxsearch?"
               f"searchword={encoded}&bidSort=0&buyerName=&projectId=&pinMu=0&"
               f"bidType=0&dbselect=infox&kw={encoded}&start_time=&end_time=&page={page}")
        
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=15, context=SSL_CTX)
            html = resp.read().decode('utf-8', errors='replace')
            resp.close()
            
            # 从 JS 变量中提取真实 URL
            # CCGP 格式: 列表数据在 inline JS 中
            urls = re.findall(r'href=["\']([^"\']+ccgp\.gov\.cn/[^"\']+)["\']', html)
            
            # 过滤只保留内容页
            content_urls = []
            for u in urls:
                # 排除 CSS/JS/图片等静态资源
                if any(x in u for x in ['.css', '.js', '.png', '.jpg', '.gif', 'inc.css']):
                    continue
                # 只留详情页
                if '/cgzhgg/' in u or '/cggg/' in u or '/zxgg/' in u:
                    content_urls.append(u)
            
            results.extend(content_urls)
            print(f"  [{keyword}] p{page}: +{len(content_urls)} 条")
            
        except Exception as e:
            print(f"  [{keyword}] p{page}: FAIL - {e}")
        
        time.sleep(0.5)
    
    return results

def fetch_detail(url):
    """抓取详情页，提取结构化数据"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=15, context=SSL_CTX)
        html = resp.read().decode('utf-8', errors='replace')
        resp.close()
        
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        
        def extract(patterns):
            for p in patterns:
                m = re.search(p, text, re.DOTALL)
                if m:
                    val = m.group(1).strip()
                    if val:
                        return val[:100]
            return ""
        
        return {
            "url": url,
            "title": extract([r'<title>([^<]+)</title>']),
            "company": extract([
                r'招标[人方][：:]\s*([^\s，,。]{2,40})',
                r'采购[人方][：:]\s*([^\s，,。]{2,40})',
            ]),
            "budget": extract([
                r'预算[：:]\s*[￥$]?\s*([\d,，.]+\s*(?:万|元|千万)?)',
                r'采购预算[：:]\s*([\d,，.]+\s*(?:万|元)?)',
                r'金额[：:]\s*([\d,，.]+\s*(?:万|元)?)',
            ]),
            "bid_deadline": extract([
                r'(?:截止?|截稿)[^0-9]*(\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}[日]?)',
                r'投标截止[^0-9]*(\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}[日]?)',
            ]),
            "contact": extract([
                r'联系人[：:]\s*([^\s，,]{2,20})',
                r'电话[：:]\s*([\d\-\s]{7,20})',
            ]),
            "found_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    except Exception as e:
        return None

def main():
    print("=" * 60)
    print("[bid-watcher] 测试运行")
    print("=" * 60)
    
    all_urls = []
    
    # Step 1: 搜索 CCGP
    print("\n[Step 1] 搜索政府采购网...")
    for kw in KEYWORDS:
        urls = fetch_ccgp(kw, max_pages=2)
        all_urls.extend(urls)
        time.sleep(0.3)
    
    # 去重
    all_urls = list(set(all_urls))
    print(f"\n共找到 {len(all_urls)} 个唯一 URL")
    
    if not all_urls:
        print("[!] 没有找到任何结果，检查网络和平台可用性")
        return
    
    # Step 2: 抓取详情
    print(f"\n[Step 2] 抓取前 {min(10, len(all_urls))} 个详情页...")
    details = []
    
    for i, url in enumerate(all_urls[:10], 1):
        short = url.split('/')[-1][:40]
        print(f"[{i}/10] {short}")
        
        detail = fetch_detail(url)
        if detail:
            title = detail.get('title', '无标题')[:35] if detail.get('title') else '无标题'
            budget = detail.get('budget', '')[:15] if detail.get('budget') else '无预算'
            print(f"  OK | {title}")
            print(f"      预算:{budget}")
            details.append(detail)
        else:
            print(f"  FAIL")
        
        time.sleep(0.3)
    
    # 统计
    print("\n" + "=" * 60)
    print("[统计]")
    print(f"  总URL: {len(all_urls)}")
    print(f"  成功抓取: {len(details)}")
    
    has_budget = sum(1 for d in details if d.get('budget'))
    has_company = sum(1 for d in details if d.get('company'))
    has_deadline = sum(1 for d in details if d.get('bid_deadline'))
    
    print(f"  有预算: {has_budget}/{len(details)}")
    print(f"  有公司: {has_company}/{len(details)}")
    print(f"  有截止: {has_deadline}/{len(details)}")
    
    # 保存
    out = f"C:\\Users\\16323\\.openclaw\\workspace\\skills\\bid-watcher\\data\\bids_parsed_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({
            "urls": all_urls,
            "details": details,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n已保存: {out}")

if __name__ == "__main__":
    main()
