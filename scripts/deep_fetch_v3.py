#!/usr/bin/env python3
"""
深化抓取：基于中国政府采购网(ccgp.gov.cn)和竞争公司名搜索
"""
import urllib.request
import urllib.parse
import json
import time
import re
from datetime import datetime

COMPETITORS = {
    "先导智能": "无锡先导智能装备股份有限公司",
    "海目星": "海目星激光科技集团股份有限公司",
    "赢合科技": "深圳市赢合科技股份有限公司",
    "联赢激光": "深圳市联赢激光股份有限公司"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://search.ccgp.gov.cn/",
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

def extract_tender_links(html):
    """从搜索结果页提取招标链接"""
    # ccgp.gov.cn 链接格式
    links = re.findall(r'(http://www\.ccgp\.gov\.cn/cggg/[^\s"]+\.htm)', html)
    return list(set(links))

def extract_list_info(html):
    """从搜索列表页提取概览信息"""
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    
    # 找总条数
    total_match = re.search(r'共找到\s*(\d+)\s*条', text)
    total = int(total_match.group(1)) if total_match else 0
    
    # 提取当前页的条目（标题+时间）
    items = []
    # 格式: "锂电池..." 后面跟时间
    # 更通用的方式：搜索 *.htm 附近的标题文本
    titles = re.findall(r'title="([^"]+)"', html)
    dates = re.findall(r'(\d{4}\.\d{2}\.\d{2})', html)
    
    return {
        "total": total,
        "titles": titles[:20],
        "dates": dates[:20]
    }

def parse_tender_detail(url):
    """解析单个招标详情页"""
    html = fetch(url)
    if not html:
        return None
    
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    
    # 提取字段
    result = {
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
            r'(\d{4}年\d{1,2}月\d{1,2}日)',
        ]),
        "contact": extract(text, [
            r'联系人[：:]\s*([^\s，,]{2,20})',
            r'电话[：:]\s*([\d\-\s]{7,20})',
            r'联系方式[：:]\s*([^\n\r]{5,50})',
        ]),
        "description": extract(text, [
            r'项目概况[：:][^\n\r]{10,200}',
            r'采购内容[：:][^\n\r]{10,200}',
        ]),
        "found_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    return result

def extract(text, patterns):
    for p in patterns:
        m = re.search(p, text)
        if m:
            val = m.group(1).strip()
            if val:
                return val[:100]
    return "未知"

def search_ccgp(keyword, max_pages=3):
    """搜索政府采购网"""
    encoded = urllib.parse.quote(keyword)
    all_links = []
    
    for page in range(1, max_pages + 1):
        page_index = page
        url = (
            f"https://search.ccgp.gov.cn/bxsearch?searchtype=1&keyword={encoded}"
            f"&bidSort=0&buyerName=&projectId=&pinMu=0&bidType=0&dbselect=downx"
            f"&kwtype=0&powerName=&pppStatus=0&agentName=&start_time=&end_time="
            f"&timeType=0&displayZone=&zoneId=&pppStatus=0&agentName=&page_index={page_index}"
        )
        
        html = fetch(url)
        if not html:
            continue
        
        if page == 1:
            info = extract_list_info(html)
            print(f"  关键词『{keyword}』共找到 {info['total']} 条\n")
        
        links = extract_tender_links(html)
        all_links.extend(links)
        print(f"  第{page}页: +{len(links)} 条链接")
        time.sleep(0.5)
    
    return all_links

def main():
    all_details = []
    seen_urls = set()
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 深化抓取 - 政府采购网\n")
    
    # Step 1: 搜索各关键词
    keywords = [
        "锂电池",
        "储能",
        "装配段",
        "锂电设备",
        "电池生产设备",
    ]
    
    # Step 2: 搜索竞争公司
    competitor_keywords = [
        "先导智能",
        "海目星",
        "赢合科技",
        "联赢激光",
    ]
    
    all_keywords = keywords + competitor_keywords
    
    for kw in all_keywords:
        print(f"\n[搜索] {kw}")
        links = search_ccgp(kw, max_pages=2)
        print(f"  去重前: {len(links)} 条")
        
        new_links = [l for l in links if l not in seen_urls]
        seen_urls.update(links)
        print(f"  新增: {len(new_links)} 条")
    
    unique_links = list(seen_urls)
    print(f"\n{'='*50}")
    print(f"共 {len(unique_links)} 个唯一招标页面")
    print("开始抓取详情...\n")
    
    # Step 3: 抓取每个详情页
    for i, url in enumerate(unique_links, 1):
        print(f"[{i}/{len(unique_links)}] {url.split('/')[-1][:40]}...")
        
        try:
            detail = parse_tender_detail(url)
        except Exception as e:
            detail = None
        if detail:
            all_details.append(detail)
            title = detail['title'][:35] if detail['title'] != '未知' else '无标题'
            budget = detail['budget'][:15] if detail['budget'] != '未知' else '无预算'
            company = detail['company'][:15] if detail['company'] != '未知' else '无公司'
            print(f"  [OK] {title}")
            print(f"       预算:{budget} | 公司:{company}")
        else:
            print(f"  [FAIL]")
        
        time.sleep(0.3)
    
    # 保存
    out = f"C:\\Users\\16323\\.openclaw\\workspace\\data\\bid_details_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(all_details, f, ensure_ascii=False, indent=2)
    
    # 统计
    has_budget = sum(1 for d in all_details if d['budget'] != '未知')
    has_company = sum(1 for d in all_details if d['company'] != '未知')
    has_deadline = sum(1 for d in all_details if d['bid_deadline'] != '未知')
    has_contact = sum(1 for d in all_details if d['contact'] != '未知')
    
    print(f"\n{'='*50}")
    print(f"完成! 抓取 {len(all_details)}/{len(unique_links)} 个页面")
    print(f"保存: {out}")
    print(f"\n数据质量:")
    print(f"  有预算: {has_budget}/{len(all_details)}")
    print(f"  有公司: {has_company}/{len(all_details)}")
    print(f"  有截止时间: {has_deadline}/{len(all_details)}")
    print(f"  有联系方式: {has_contact}/{len(all_details)}")

if __name__ == "__main__":
    main()
