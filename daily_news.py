#!/usr/bin/env python3
"""
每日财经早报 - 量化选股版
数据来源：东方财富
"""

import os, time, hmac, hashlib, base64, urllib.parse, json, requests
from datetime import datetime

DINGTALK_TOKEN = os.environ.get('DINGTALK_TOKEN', 'a083b59f98dfb5bd1c275b87df05ebf3c32648ced0dc2379953ec55334e903a7')
DINGTALK_SECRET = os.environ.get('DINGTALK_SECRET', 'SEC7f153faacf6efa03646e1fb023a5be97dd49df777f051a05c86b03245ec895ec')

def get_timestamp(): return str(int(time.time() * 1000))
def generate_sign(timestamp, secret):
    s = '{}\n{}'.format(timestamp, secret)
    return urllib.parse.quote(base64.b64encode(hmac.new(secret.encode(), s.encode(), hashlib.sha256).digest()).decode())

def get_market_index():
    indices = []
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'}
    for code, name in {'sh000001': '上证', 'sz399001': '深证', 'sz399006': '创业板', 'sh000300': '沪深300'}.items():
        try:
            r = requests.get(f'https://push2.eastmoney.com/api/qt/stock/get', params={'secid': code, 'fields': 'f2,f3', 'ut': 'bd1d9ddb04089700cf9c27f6f7426281'}, headers=headers, timeout=10)
            if r.status_code == 200 and 'data' in r.json(): 
                d = r.json()['data']
                indices.append({'name': name, 'price': d.get('f2', '--'), 'change': d.get('f3', 0)})
        except: pass
    return indices

def get_hot_stocks():
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'}
    try:
        r = requests.get('https://push2.eastmoney.com/api/qt/clist/get', params={'pn': 1, 'pz': 30, 'po': 1, 'np': 1, 'ut': 'bd1d9ddb04089700cf9c27f6f7426281', 'fltt': 2, 'invt': 2, 'fid': 'f3', 'fs': 'm:0+t:6,m:0+t:13,m:0+t:80,m:1+t:23,m:1+t:81', 'fields': 'f2,f3,f5,f6,f7,f8,f10,f12,f14,f15,f16'}, headers=headers, timeout=15)
        if r.status_code == 200 and 'data' in r.json() and 'diff' in r.json()['data']:
            return [{'name': i.get('f14','?'), 'code': i.get('f12',''), 'price': i.get('f2',0), 'change_pct': i.get('f3',0), 'volume': i.get('f5',0), 'amount': i.get('f6',0), 'amplitude': i.get('f7',0), 'turnover': i.get('f8',0), 'pe': i.get('f10',0), 'high': i.get('f15',0), 'low': i.get('f16',0)} for i in r.json()['data']['diff']]
    except: pass
    return []

def get_finance_news():
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://news.eastmoney.com/'}
    try:
        r = requests.get('https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html', headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if 'LivesList' in data: return [{'title': i.get('title','')} for i in data['LivesList'][:5]]
    except: pass
    return []

def format_amount(a):
    try:
        a = float(a)
        if a >= 1e8: return f"{a/1e8:.1f}亿"
        elif a >= 1e4: return f"{a/1e4:.0f}万"
        return f"{a:.0f}"
    except: return str(a)

def quant_select(stocks, indices):
    if not stocks: return []
    avg = sum(i.get('change',0) for i in indices)/len(indices) if indices else 0
    result = []
    for s in stocks:
        code, change, turnover, pe = str(s.get('code','')), s.get('change_pct',0), s.get('turnover',0), s.get('pe',0)
        is_kcb, is_cyb = code.startswith('688'), code.startswith('3')
        limit = 19.9 if (is_kcb or is_cyb) else 9.9
        score, tags = 0, []
        if change >= limit:
            score += 50 if turnover < 15 else 40 if 40 >= turnover >= 10 else 20
            tags.append("缩量涨停" if turnover < 15 else "封板良好" if 40 >= turnover >= 10 else "高位接力")
        elif change >= 19: score, tags = 35, ["冲击涨停"]
        elif change >= 10: score, tags = (45, ["量价齐升"]) if 25 >= turnover >= 10 else (25, ["强势"])
        elif change >= 7: score, tags = (35, ["稳步放量"]) if 20 >= turnover >= 8 else (20, ["走势良好"])
        elif change >= 4: score, tags = (25, ["温和放量"]) if 15 >= turnover >= 5 else (15, ["小幅上涨"])
        try:
            if 1e8 < float(s.get('amount',0)) < 5e9: score += 10
        except: pass
        if change > avg + 3: score += 10; tags.append("强于大盘")
        try:
            if 0 < float(pe if pe and pe != '-' else 0) < 60: score += 5
        except: pass
        result.append({'stock': s, 'score': score, 'tags': tags, 'limit': limit})
    result.sort(key=lambda x: x['score'], reverse=True)
    return result[:5]

def get_action(item, indices):
    s, change, turnover, price = item['stock'], item['stock'].get('change_pct',0), item['stock'].get('turnover',0), item['stock'].get('price',0)
    limit = item['limit']
    if change >= limit: return "明日高开<3%可追，止损5%" if turnover < 15 else "谨慎追板，设7%止损"
    elif change >= 19: return "尾盘竞价介入，止损3%"
    elif change >= 10: return "回调至今日均价可入，止损5%"
    elif change >= 7: return "回调MA5支撑介入，止损4%"
    elif change >= 4: return "逢低关注，止损3%"
    return "观望，不追高"

def get_position(indices):
    avg = sum(i.get('change',0) for i in indices)/len(indices) if indices else 0
    return "6-7成" if avg > 1.5 else "5-6成" if avg > 0.5 else "4-5成" if avg > -0.5 else "2-3成" if avg > -1.5 else "1-2成"

def generate_report():
    today = datetime.now().strftime('%Y年%m月%d日')
    indices, hot_stocks, news, selected = get_market_index(), get_hot_stocks(), get_finance_news(), quant_select(get_hot_stocks(), indices)
    report = f"# 📊 量化选股早报\n\n**{today}**\n\n---\n\n## 【大盘行情】\n\n"
    for idx in indices: report += f"{idx['name']}：{idx['price']} {'🔺' if idx['change']>0 else '🔻'} {idx['change']:+.2f}%\n"
    report += f"\n建议仓位：{get_position(indices)}\n\n---\n\n## 【财经要闻】\n\n"
    for i, n in enumerate(news, 1): report += f"{i}. {n['title']}\n"
    report += "\n---\n\n## 【量化精选】\n\n"
    for i, item in enumerate(selected, 1):
        s, code = item['stock'], str(item['stock'].get('code',''))
        board = "科创" if code.startswith('688') else "创业" if code.startswith('3') else "主板"
        report += f"**{i}. {s['name']}** [{board}]\n代码：{s['code']} | 现价：¥{s['price']} {'🔺' if s['change_pct']>0 else '🔻'} {s['change_pct']:+.2f}%\n换手：{s.get('turnover',0):.1f}% | 成交：{format_amount(s.get('amount',0))}\n标签：{'、'.join(item['tags'])}\n**操作：{get_action(item, indices)}**\n\n"
    return report

def send_dingtalk(msg):
    try:
        r = requests.post(f"https://oapi.dingtalk.com/robot/send?access_token={DINGTALK_TOKEN}&timestamp={get_timestamp()}&sign={generate_sign(get_timestamp(), DINGTALK_SECRET)}", headers={'Content-Type': 'application/json'}, data=json.dumps({"msgtype": "markdown", "markdown": {"title": "量化选股早报", "text": msg}}), timeout=15)
        return r.json().get('errcode') == 0
    except: return False

def main():
    print("开始生成早报...")
    success = send_dingtalk(generate_report())
    print("✅ 发送成功" if success else "❌ 发送失败")
    return success

if __name__ == "__main__": main()
