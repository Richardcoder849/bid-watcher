#!/usr/bin/env python3
"""修复版：跟随 Bing 重定向并过滤出真实招标页面"""
import urllib.request
import urllib.parse
import json
import time
import re
import ssl
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 已知可用的招标平台（绕过搜索引擎）
DIRECT_SITES = [
    "ccgp.gov.cn",
    "ctexw.com",
    "jianyu360.com",
    "bidcenter.com.cn",
]

def follow_redirect(url, max_follows=3):
    """跟随重定向，获取最终 URL"""
    if 'r.bing.com' in url or 'th.bing.com' in url:
        return None  # Bing 中转页不跟
    try:
        req = urllib.request.Request(url, headers=HEADERS, method='HEAD')
        resp = urllib.request.urlopen(req, timeout=10)
        final_url = resp.geturl()
        resp.close()
        return final_url
    except:
        return None

def load_raw():
    with open(r'C:\Users\16323\.openclaw\workspace\skills\bid-watcher\data\bids_raw_20260421.json','r',encoding='utf-8') as f:
        return json.load(f)

def filter_real_bids(raw):
    """过滤出真实招标页面"""
    good_urls = set()
    bad_urls = []
    
    for r in raw:
        url = r['url']
        
        # 跳过 Bing 中转
        if 'r.bing.com' in url or 'th.bing.com' in url:
            bad_urls.append((url, 'bing_redirect'))
            continue
        
        # 跳过搜索页本身
        if any(x in url for x in ['baidu.com', 'bing.com', 'sogou.com', 'so.com', 'google.com']):
            bad_urls.append((url, 'search_engine'))
            continue
        
        # 尝试访问
        final_url = follow_redirect(url)
        if final_url and final_url != url:
            good_urls.add(final_url)
        elif final_url:
            good_urls.add(url)
    
    return list(good_urls), bad_urls

def search_ccgp(keyword, max_pages=2):
    """直接搜政府采购网"""
    encoded = urllib.parse.quote(keyword)
    results = []
    
    for page in range(1, max_pages + 1):
        url = f"http://search.ccgp.gov.cn/bxsearch?searchword={encoded}&bidSort=0&buyerName=&projectId=&pinMu=0&bidType=0&dbselect=infox&kw=&start_time=&end_time=&page={page}"
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=15)
            html = resp.read().decode('utf-8', errors='replace')
            resp.close()
            
            # 提取链接
            links = re.findall(r'href="(/bxsearch[^\s"]+)"', html)
            for link in links:
                full_url = "http://search.ccgp.gov.cn" + link
                if full_url not in results:
                    results.append(full_url)
            
            print(f"  [{keyword}] page{page}: +{len(links)}")
        except Exception as e:
            print(f"  [{keyword}] page{page}: FAIL - {e}")
        
        time.sleep(0.5)
    
    return results

def main():
    print("=" * 50)
    print("[Step 1] 搜索 raw 数据中的真实 URL")
    
    raw = load_raw()
    good, bad = filter_real_bids(raw)
    print(f"\n原始: {len(raw)} 条")
    print(f"有效: {len(good)} 条")
    print(f"无效: {len(bad)} 条 (Bing中转/搜索引擎)")
    
    # 统计无效原因
    from collections import Counter
    reasons = Counter(b[1] for b in bad)
    for reason, cnt in reasons.most_common():
        print(f"  {reason}: {cnt}")
    
    print("\n有效 URL 样例:")
    for u in list(good)[:5]:
        print(f"  {u[:80]}")
    
    print("\n" + "=" * 50)
    print("[Step 2] 直接搜索政府采购网")
    
    keywords = ["锂电池", "储能", "锂电设备"]
    ccgp_results = []
    
    for kw in keywords:
        urls = search_ccgp(kw, max_pages=2)
        ccgp_results.extend(urls)
        time.sleep(0.5)
    
    # 去重
    ccgp_results = list(set(ccgp_results))
    print(f"\n政府采购网共找到: {len(ccgp_results)} 条")
    
    print("\n" + "=" * 50)
    print("[Step 3] 汇总有效 URL")
    
    all_good = list(set(good + ccgp_results))
    print(f"合计有效 URL: {len(all_good)} 条")
    
    # 保存
    out = r"C:\Users\16323\.openclaw\workspace\skills\bid-watcher\data\bids_filtered_20260421.json"
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({
            "direct_from_bing": good,
            "from_ccgp": ccgp_results,
            "all": all_good,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }, f, ensure_ascii=False, indent=2)
    
    print(f"已保存: {out}")
    
    return all_good

if __name__ == "__main__":
    main()
