#!/usr/bin/env python3
"""快速测试：只跑2个关键词验证新关键词效果"""
import urllib.request
import urllib.parse
import ssl
import re
import time
import json
import os
from datetime import datetime

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

KEYWORDS = [
    "储能系统设备采购",
    "电池生产线设备采购",
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")

DELAY = 5

def fetch_ccgp(keyword, max_pages=3):
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
            
            js_urls = re.findall(r'href=["\']([^"\']+ccgp\.gov\.cn[^"\']+)["\']', html)
            
            content_urls = []
            for u in js_urls:
                if any(x in u for x in ['.css', '.js', '.png', '.jpg', '.gif', 'inc.css']):
                    continue
                if any(x in u for x in ['/cgzhgg/', '/cggg/', '/zxgg/', '/dfgg/']):
                    content_urls.append(u)
            
            results.extend(content_urls)
            print(f"  [{keyword}] p{page}: +{len(content_urls)}")
            
        except Exception as e:
            print(f"  [{keyword}] p{page}: FAIL - {e}")
        
        time.sleep(DELAY)
    
    return results

def main():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    all_results = []
    
    print(f"[{timestamp}] 快速测试：{len(KEYWORDS)} 个新关键词\n")
    
    for kw in KEYWORDS:
        print(f"[{kw}]")
        urls = fetch_ccgp(kw, max_pages=3)
        
        for url in urls:
            all_results.append({
                "keyword": kw,
                "url": url,
                "platform": "ccgp",
                "found_at": timestamp
            })
        
        time.sleep(2)
    
    # 保存
    os.makedirs(DATA_DIR, exist_ok=True)
    out = f"{DATA_DIR}/bids_raw_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n共 {len(all_results)} 条，已保存: {out}")
    
    # 打印样例
    if all_results:
        print("\n样例 URL:")
        for r in all_results[:5]:
            print(f"  [{r['keyword']}] {r['url'][:80]}")

if __name__ == "__main__":
    main()
