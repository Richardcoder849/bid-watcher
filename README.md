# Bid Watcher 📋

> 投标情报监控系统

## 功能

监控锂电池/储能/装配段行业招标信息，追踪竞争对手投标动态：

- **无锡先导** — 先导智能
- **海目星** — 海目星激光
- **赢合科技** — 赢合科技
- **联赢激光** — 联赢激光

## 特点

- 从北极星能源网、能源界网、新浪财经等平台自动采集招标信息
- 自动提取公司名、预算金额、项目规模
- S/A/B/C 四级优先级评分
- 输出 Excel 看板报告（带颜色标记）

## 安装

```bash
clawhub install bid-watcher
```

## 使用

```bash
# 搜索招标信息
python scripts/search_bids.py

# 提取公司/预算 + 评分
python scripts/enrich_bids.py

# 生成 Excel 报告
python scripts/generate_report.py --format excel
```

## 输出

- Excel 报告：`data/bid_report_W*.xlsx`
- Markdown 报告：`data/bid_report_W*.md`
- 原始数据：`data/bids_raw_YYYYMMDD.json`

## License

MIT
