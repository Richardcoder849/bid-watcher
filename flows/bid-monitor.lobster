name: bid-monitor
description: 投标情报监控流程 - 搜索 > 解析 > 补充背景 > 生成报告 > 发送邮件 > 存档

steps:
  - id: search
    command: exec --command "python search_bids.py" --workdir "C:\\Users\\16323\\.openclaw\\workspace\\skills\\bid-watcher\\scripts" --timeout 120
    description: "Step 1: Bing 搜索招标信息"

  - id: parse
    command: exec --command "python parse_bids.py" --workdir "C:\\Users\\16323\\.openclaw\\workspace\\skills\\bid-watcher\\scripts" --timeout 180
    condition: $search.exit_code == 0
    description: "Step 2: 抓取详情页 + 结构化解析 + URL去重"

  - id: enrich
    command: exec --command "python enrich_company.py" --workdir "C:\\Users\\16323\\.openclaw\\workspace\\skills\\bid-watcher\\scripts" --timeout 60
    condition: $parse.exit_code == 0
    description: "Step 3: 补充公司背景 + 优先级评分"

  - id: generate_report
    command: exec --command "python generate_report.py" --workdir "C:\\Users\\16323\\.openclaw\\workspace\\skills\\bid-watcher\\scripts" --timeout 60
    condition: $enrich.exit_code == 0
    description: "Step 4: 生成周报表格"

  - id: send_email
    command: exec --command "python send_email.py" --workdir "C:\\Users\\16323\\.openclaw\\workspace\\skills\\bid-watcher\\scripts" --timeout 30
    condition: $generate_report.exit_code == 0
    description: "Step 5: 发送邮件（需配置环境变量）"
