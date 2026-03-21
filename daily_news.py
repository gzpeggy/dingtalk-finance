#!/usr/bin/env python3
"""
每日财经早报 - 量化选股版
数据来源：东方财富 + 新浪财经
"""

import os
import re
import time
import hmac
import hashlib
import base64
import urllib.parse
import json
import requests
from datetime import datetime

# 钉钉配置
DINGTALK_TOKEN = os.environ.get('DINGTALK_TOKEN', '')
DINGTALK_SECRET = os.environ.get('DINGTALK_SECRET', '')

def get_timestamp():
    return str(int(time.time() * 1000))

def generate_sign(timestamp, secret):
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    hmac_code = hmac.new(secret.encode(), string_to_sign.encode(), digestmod=hashlib.sha256).digest()
    return urllib.parse.quote(base64.b64encode(hmac_code).decode())

def get_market_index():
    """获取大盘指数 - 使用新浪财经"""
    indices = []
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn/'}

    codes = {'sh000001': '上证指数', 'sz399001': '深证成指', 'sz399006': '创业板指', 'sh000300': '沪深300'}

    try:
        url = f"https://hq.sinajs.cn/list={','.join(codes.keys())}"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            content = response.content.decode('gbk')
            # 解析格式: var hq_str_sh000001="name,open,pre_close,price,high,low,..."
            # 字段含义: data[0]=名称, data[1]=开盘价, data[2]=昨收, data[3]=现价, data[4]=最高, data[5]=最低
            for code, name in codes.items():
                pattern = f'hq_str_{code}="([^"]*)"'
                match = re.search(pattern, content)
                if match:
                    data = match.group(1).split(',')
                    if len(data) >= 6:
                        price = float(data[3]) if data[3] else 0  # 现价在data[3]
                        yesterday = float(data[2]) if data[2] else 0  # 昨收在data[2]
                        pct = ((price - yesterday) / yesterday * 100) if yesterday > 0 else 0
                        indices.append({
                            'name': name,
                            'price': f'{price:.2f}',
                            'change': round(pct, 2)
                        })
    except Exception as e:
        print(f"❌ 获取指数失败: {e}")

    return indices

def get_hot_stocks():
    """获取涨幅榜"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://quote.eastmoney.com/'
    }

    try:
        url = 'https://push2.eastmoney.com/api/qt/clist/get'
        params = {
            'pn': 1, 'pz': 30, 'po': 1, 'np': 1,
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': 2, 'invt': 2, 'fid': 'f3',
            'fs': 'm:0+t:6,m:0+t:13,m:0+t:80,m:1+t:23,m:1+t:81',
            'fields': 'f2,f3,f5,f6,f7,f8,f10,f12,f14,f15,f16'
        }

        response = requests.get(url, params=params, headers=headers, timeout=15)

        if response.status_code == 200:
            data = response.json()
            if data and 'data' in data and data['data'] and 'diff' in data['data']:
                stocks = []
                for item in data['data']['diff'][:30]:
                    try:
                        stock = {
                            'name': item.get('f14', '?'),
                            'code': item.get('f12', ''),
                            'price': item.get('f2', 0),
                            'change_pct': float(item.get('f3', 0)) if item.get('f3') else 0,
                            'volume': item.get('f5', 0),
                            'amount': item.get('f6', 0),
                            'amplitude': float(item.get('f7', 0)) if item.get('f7') else 0,
                            'turnover': float(item.get('f8', 0)) if item.get('f8') else 0,
                            'pe': item.get('f10', 0),
                            'high': item.get('f15', 0),
                            'low': item.get('f16', 0)
                        }
                        stocks.append(stock)
                    except:
                        continue
                return stocks
    except Exception as e:
        print(f"❌ 获取涨幅榜失败: {e}")

    return []

def get_finance_news():
    """获取财经快讯"""
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://news.eastmoney.com/'
    }

    try:
        url = 'https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html'
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code == 200:
            content = response.text
            json_match = re.search(r'ajaxResult\s*=\s*(\{.*\})', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                if 'LivesList' in data:
                    return [{'title': item.get('title', '')} for item in data['LivesList'][:5]]
    except Exception as e:
        print(f"❌ 获取新闻失败: {e}")

    return []

def format_amount(amount):
    try:
        amount = float(amount)
        if amount >= 1e8: return f"{amount/1e8:.1f}亿"
        elif amount >= 1e4: return f"{amount/1e4:.0f}万"
        return f"{amount:.0f}"
    except: return str(amount)

def quant_select(stocks, indices):
    """量化选股"""
    if not stocks: return []

    avg_change = sum(idx.get('change', 0) for idx in indices) / len(indices) if indices else 0

    candidates = []
    for s in stocks:
        code = str(s.get('code', ''))
        change = s.get('change_pct', 0)
        turnover = s.get('turnover', 0)
        pe = s.get('pe', 0)
        amount = s.get('amount', 0)

        is_kcb = code.startswith('688')
        is_cyb = code.startswith('300') or code.startswith('301')
        limit = 19.9 if (is_kcb or is_cyb) else 9.9

        score, tags = 0, []

        if change >= limit:
            if turnover < 15:
                score, tags = 50, ["缩量涨停"]
            elif 40 >= turnover >= 10:
                score, tags = 40, ["封板良好"]
            else:
                score, tags = 20, ["高位接力"]
        elif change >= 19:
            score, tags = 35, ["冲击涨停"]
        elif change >= 10:
            if 25 >= turnover >= 10:
                score, tags = 45, ["量价齐升"]
            else:
                score, tags = 25, ["强势"]
        elif change >= 7:
            if 20 >= turnover >= 8:
                score, tags = 35, ["稳步放量"]
            else:
                score = 20
        elif change >= 4:
            if 15 >= turnover >= 5:
                score, tags = 25, ["温和放量"]
            else:
                score = 15

        try:
            if 1e8 < float(amount) < 5e9: score += 10
        except: pass

        if change > avg_change + 3:
            score += 10
            tags.append("强于大盘")

        try:
            pe_val = float(pe) if pe and pe != '-' else 0
            if 0 < pe_val < 60: score += 5
        except: pass

        if score > 0:
            candidates.append({'stock': s, 'score': score, 'tags': tags, 'limit': limit})

    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates[:5]

def get_action(item):
    s, change, turnover = item['stock'], item['stock'].get('change_pct', 0), item['stock'].get('turnover', 0)
    limit = item['limit']
    if change >= limit:
        return "明日高开<3%可追，止损5%" if turnover < 15 else "谨慎追板，设7%止损"
    elif change >= 19:
        return "尾盘竞价介入，止损3%"
    elif change >= 10:
        return "回调至今日均价可入，止损5%"
    elif change >= 7:
        return "回调MA5支撑介入，止损4%"
    elif change >= 4:
        return "逢低关注，止损3%"
    return "观望，不追高"

def get_position(indices):
    avg = sum(idx.get('change', 0) for idx in indices) / len(indices) if indices else 0
    return "6-7成" if avg > 1.5 else "5-6成" if avg > 0.5 else "4-5成" if avg > -0.5 else "2-3成" if avg > -1.5 else "1-2成"

def generate_report():
    today = datetime.now().strftime('%Y年%m月%d日')

    indices = get_market_index()
    hot_stocks = get_hot_stocks()
    news = get_finance_news()
    selected = quant_select(hot_stocks, indices)
    position = get_position(indices)

    report = f"# 📊 量化选股早报\n\n**{today}**\n\n---\n\n## 【大盘行情】\n\n"

    if indices:
        for idx in indices:
            icon = '🔺' if idx['change'] > 0 else '🔻' if idx['change'] < 0 else '➡️'
            report += f"{idx['name']}：{idx['price']} {icon} {idx['change']:+.2f}%\n"
        report += f"\n建议仓位：{position}\n"
    else:
        report += "数据获取失败\n"

    report += "\n---\n\n## 【财经要闻】\n\n"

    if news:
        for i, n in enumerate(news, 1):
            report += f"{i}. {n['title']}\n"
    else:
        report += "数据获取失败\n"

    report += "\n---\n\n## 【量化精选】\n\n"

    if selected:
        for i, item in enumerate(selected, 1):
            s = item['stock']
            code = str(s.get('code', ''))
            board = "科创" if code.startswith('688') else "创业" if code.startswith('3') else "主板"
            action = get_action(item)
            icon = '🔺' if s['change_pct'] > 0 else '🔻'

            report += f"**{i}. {s['name']}** [{board}]\n"
            report += f"代码：{s['code']} | 现价：¥{s['price']} {icon} {s['change_pct']:+.2f}%\n"
            report += f"换手：{s.get('turnover', 0):.1f}% | 成交：{format_amount(s.get('amount', 0))}\n"
            report += f"标签：{'、'.join(item['tags'])}\n"
            report += f"**操作：{action}**\n\n"
    else:
        report += "数据获取失败\n"

    return report

def send_dingtalk(msg):
    try:
        timestamp = get_timestamp()
        sign = generate_sign(timestamp, DINGTALK_SECRET)
        url = f"https://oapi.dingtalk.com/robot/send?access_token={DINGTALK_TOKEN}&timestamp={timestamp}&sign={sign}"

        response = requests.post(
            url,
            headers={'Content-Type': 'application/json'},
            data=json.dumps({"msgtype": "markdown", "markdown": {"title": "量化选股早报", "text": msg}}),
            timeout=15
        )
        result = response.json()
        return result.get('errcode') == 0
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        return False

def main():
    report = generate_report()
    return send_dingtalk(report)

if __name__ == "__main__":
    main()
