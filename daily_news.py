#!/usr/bin/env python3
"""
每日财经早报 - 量化精选版
数据来源：东方财富
核心功能：动态分析 + 精选明日潜力股 + 实时操作建议
"""

import os
import time
import hmac
import hashlib
import base64
import urllib.parse
import json
import requests
from datetime import datetime

# 钉钉配置
DINGTALK_TOKEN = os.environ.get('DINGTALK_TOKEN', 'a083b59f98dfb5bd1c275b87df05ebf3c32648ced0dc2379953ec55334e903a7')
DINGTALK_SECRET = os.environ.get('DINGTALK_SECRET', 'SEC7f153faacf6efa03646e1fb023a5be97dd49df777f051a05c86b03245ec895ec')

def get_timestamp():
    return str(int(time.time() * 1000))

def generate_sign(timestamp, secret):
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    hmac_code = hmac.new(secret.encode(), string_to_sign.encode(), digestmod=hashlib.sha256).digest()
    return urllib.parse.quote(base64.b64encode(hmac_code).decode())

def get_market_index():
    """获取大盘指数（上证、深证、创业板、沪深300）"""
    indices = []
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'}
    
    index_codes = {
        'sh000001': '上证指数',
        'sz399001': '深证成指', 
        'sz399006': '创业板指',
        'sh000300': '沪深300'
    }
    
    for code, name in index_codes.items():
        try:
            url = f'https://push2.eastmoney.com/api/qt/stock/get'
            params = {'secid': code, 'fields': 'f2,f3,f4,f5,f6,f7,f8', 'ut': 'bd1d9ddb04089700cf9c27f6f7426281'}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    d = data['data']
                    indices.append({
                        'name': name,
                        'price': d.get('f2', '--'),
                        'change': d.get('f3', 0),
                        'change_amt': d.get('f4', 0),
                        'volume': d.get('f5', 0),
                        'amount': d.get('f6', 0)
                    })
        except Exception as e:
            print(f"获取{name}失败: {e}")
    
    print(f"✅ 获取到 {len(indices)} 个大盘指数")
    return indices

def get_hot_stocks():
    """获取涨幅榜股票"""
    stocks = []
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'}
    
    try:
        url = 'https://push2.eastmoney.com/api/qt/clist/get'
        params = {
            'pn': 1, 'pz': 20, 'po': 1, 'np': 1,
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': 2, 'invt': 2, 'fid': 'f3',
            'fs': 'm:0+t:6,m:0+t:13,m:0+t:80,m:1+t:23,m:1+t:81',
            'fields': 'f2,f3,f4,f5,f6,f7,f8,f10,f12,f14,f15,f16,f17,f18'
        }
        response = requests.get(url, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'diff' in data['data']:
                for item in data['data']['diff'][:20]:
                    stocks.append({
                        'name': item.get('f14', '未知'),
                        'code': item.get('f12', ''),
                        'price': item.get('f2', 0),
                        'change_pct': item.get('f3', 0),
                        'change_amt': item.get('f4', 0),
                        'volume': item.get('f5', 0),
                        'amount': item.get('f6', 0),
                        'amplitude': item.get('f7', 0),
                        'turnover': item.get('f8', 0),
                        'pe': item.get('f10', 0),
                        'high': item.get('f15', 0),
                        'low': item.get('f16', 0)
                    })
                print(f"✅ 获取到 {len(stocks)} 只涨幅榜股票")
                return stocks
    except Exception as e:
        print(f"获取热点股票失败: {e}")
    return []

def get_finance_news():
    """获取财经快讯"""
    news_list = []
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://news.eastmoney.com/'}
    
    try:
        response = requests.get('https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html',
                                headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if 'LivesList' in data:
                for item in data['LivesList'][:10]:
                    news_list.append({
                        'title': item.get('title', ''),
                        'time': item.get('showtime', ''),
                        'summary': item.get('digest', '')[:60] if item.get('digest') else ''
                    })
                print(f"✅ 获取到 {len(news_list)} 条财经新闻")
                return news_list
    except Exception as e:
        print(f"获取新闻失败: {e}")
    return []

def format_amount(amount):
    try:
        amount = float(amount)
        if amount >= 100000000: return f"{amount/100000000:.2f}亿"
        elif amount >= 10000: return f"{amount/10000:.2f}万"
        return f"{amount:.2f}"
    except: return str(amount)

def select_best_stocks(stocks, indices):
    """量化精选：选出3-5只明日潜力股"""
    if not stocks or not indices:
        return []
    
    avg_change = sum(idx.get('change', 0) for idx in indices) / len(indices) if indices else 0
    
    candidates = []
    for stock in stocks:
        code = str(stock.get('code', ''))
        change = stock.get('change_pct', 0)
        turnover = stock.get('turnover', 0)
        amplitude = stock.get('amplitude', 0)
        pe = stock.get('pe', 0)
        amount = stock.get('amount', 0)
        price = stock.get('price', 0)
        high = stock.get('high', 0)
        low = stock.get('low', 0)
        
        is_kcb = code.startswith('688')
        is_cyb = code.startswith('300') or code.startswith('301')
        limit_up = 19.9 if (is_kcb or is_cyb) else 9.9
        
        score = 0
        reasons = []
        
        # 涨停股评分
        if change >= limit_up:
            if turnover >= 15 and turnover <= 35:
                score += 30
                reasons.append("封板质量好")
            elif turnover > 35:
                score += 10
                reasons.append("换手过高")
            elif turnover < 15:
                score += 20
                reasons.append("缩量涨停")
        
        # 接近涨停
        elif change >= 19:
            score += 25
            reasons.append("接近涨停")
        
        # 大涨股（7-15%）
        elif change >= 7 and change < limit_up:
            if turnover >= 10 and turnover <= 25:
                score += 35
                reasons.append("量价配合良好")
            elif turnover > 25:
                score += 15
            else:
                score += 20
                reasons.append("稳步上涨")
        
        # 温和上涨（3-7%）
        elif change >= 3 and change < 7:
            if turnover >= 5 and turnover <= 15:
                score += 25
                reasons.append("温和放量")
            else:
                score += 15
        
        # 成交额
        try:
            amount_val = float(amount)
            if 1e8 < amount_val < 5e9:
                score += 10
                reasons.append("成交活跃")
            elif amount_val <= 1e8:
                score -= 10
        except: pass
        
        # 振幅
        try:
            amp = float(amplitude)
            if 3 <= amp <= 8:
                score += 10
                reasons.append("波动适中")
            elif amp > 10:
                score -= 5
        except: pass
        
        # 市盈率
        try:
            pe_val = float(pe) if pe and pe != '-' else 0
            if 0 < pe_val < 50:
                score += 5
            elif pe_val >= 100:
                score -= 10
        except: pass
        
        # 跑赢大盘
        if change > avg_change + 2:
            score += 10
            reasons.append("强于大盘")
        
        # 技术位
        try:
            support = round(float(low) * 1.005, 2)
            resist = round(float(high) * 0.998, 2)
        except:
            support, resist = 0, 0
        
        candidates.append({
            'stock': stock,
            'score': score,
            'reasons': reasons,
            'support': support,
            'resist': resist,
            'is_limit_up': change >= limit_up
        })
    
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates[:5]

def generate_operation_advice(stock_data, indices, trend):
    stock = stock_data['stock']
    code = str(stock.get('code', ''))
    name = stock['name']
    change = stock['change_pct']
    price = stock['price']
    turnover = stock.get('turnover', 0)
    
    is_kcb = code.startswith('688')
    is_cyb = code.startswith('300') or code.startswith('301')
    limit_up = 19.9 if (is_kcb or is_cyb) else 9.9
    
    advice = []
    action = "观望"
    
    avg_change = sum(idx.get('change', 0) for idx in indices) / len(indices) if indices else 0
    
    if change >= limit_up:
        if stock_data['is_limit_up']:
            advice.append("今日涨停，明日关注开盘溢价")
            if turnover < 15:
                advice.append("缩量封板，强势信号")
                action = "若高开<3%可轻仓介入"
            else:
                advice.append("换手适中")
                action = "设5%止损，追板需谨慎"
    elif change >= 19:
        advice.append("接近涨停，明日有封板预期")
        action = "可尾盘介入，止损3%"
    elif change >= 10:
        advice.append("强势上涨，回调可关注")
        action = "回调到开盘价附近可介入"
    elif change >= 7:
        if turnover >= 10:
            advice.append("量价齐升，趋势良好")
            action = "持有为主，回调加仓"
        else:
            advice.append("稳步推升")
            action = "可持股，等待加速"
    elif change >= 4:
        advice.append("走势健康")
        action = "回调至MA5介入"
    else:
        advice.append("关注明日放量突破")
        action = "观望为主"
    
    if avg_change < -1:
        advice.append(f"⚠️ 大盘走弱，需控仓")
        action = "轻仓观望"
    elif avg_change > 1:
        advice.append(f"大盘强势")
    
    if abs(avg_change) < 0.5:
        position = "3-5成"
    elif avg_change > 1 or avg_change < -1:
        position = "1-3成"
    else:
        position = "5成左右"
    
    return {
        'advice': advice,
        'action': action,
        'position': position,
        'stop_loss': round(float(price) * 0.97, 2) if price else 0,
        'target': round(float(price) * (1.05 if change < limit_up else 1.15), 2) if price else 0
    }

def get_market_trend(indices):
    if not indices:
        return "震荡", "控制仓位"
    
    avg_change = sum(idx.get('change', 0) for idx in indices) / len(indices)
    
    if avg_change > 1.5:
        return "强势上涨", "可适当加仓至6-7成"
    elif avg_change > 0.5:
        return "温和上涨", "保持5-6成仓位"
    elif avg_change > -0.5:
        return "小幅震荡", "控制仓位5成左右"
    elif avg_change > -1.5:
        return "小幅回调", "降仓至3-5成"
    else:
        return "明显下跌", "轻仓1-3成观望"

def generate_report():
    today = datetime.now().strftime('%Y年%m月%d日 %H:%M')
    print("=" * 60)
    print("📊 量化精选早报 - 开始获取实时数据...")
    print("=" * 60)
    
    indices = get_market_index()
    hot_stocks = get_hot_stocks()
    news_list = get_finance_news()
    
    trend, trend_advice = get_market_trend(indices)
    selected = select_best_stocks(hot_stocks, indices)
    
    report = f"""# 📊 量化精选早报

**{today}**

---

## 【大盘实时行情】

"""
    
    if indices:
        for idx in indices:
            change = idx.get('change', 0)
            trend_icon = '🔺' if change > 0 else '🔻' if change < 0 else '➡️'
            report += f"**{idx['name']}**：{idx['price']} {trend_icon} **{change:+.2f}%**\n"
        
        report += f"\n> 市场趋势：**{trend}**\n"
        report += f"> 操作建议：{trend_advice}\n"
    else:
        report += "暂无实时数据\n"
    
    report += """---

## 🎯 【今日量化精选】（明日关注）

"""
    
    if selected:
        for i, item in enumerate(selected, 1):
            stock = item['stock']
            advice_data = generate_operation_advice(item, indices, trend)
            code = str(stock.get('code', ''))
            
            if code.startswith('688'):
                board = "科创板"
            elif code.startswith('300') or code.startswith('301'):
                board = "创业板"
            elif code.startswith('6'):
                board = "沪市主板"
            else:
                board = "深市主板"
            
            report += f"**{i}. {stock['name']}**（{board}）\n"
            report += f"   代码：{stock['code']}\n"
            report += f"   现价：¥{stock['price']} | 涨幅：{'🔺' if stock['change_pct'] > 0 else '🔻'} **{stock['change_pct']:+.2f}%**\n"
            report += f"   换手率：{stock.get('turnover', 0):.2f}% | 成交额：{format_amount(stock.get('amount', 0))}\n"
            report += f"   量化理由：{'、'.join(item['reasons'][:3]) if item['reasons'] else '综合评分优'}\n"
            report += f"   支撑位：{item['support']} | 压力位：{item['resist']}\n"
            report += f"   **操作建议：{advice_data['action']}**\n"
            report += f"   止损位：¥{advice_data['stop_loss']} | 目标位：¥{advice_data['target']}\n"
            report += f"   建议仓位：{advice_data['position']}\n\n"
    else:
        report += "暂无精选股票\n"
    
    report += """---

## 📰 【财经快讯】

"""
    
    if news_list:
        for i, news in enumerate(news_list[:6], 1):
            report += f"**{i}. {news['title']}**\n"
            if news['summary']: report += f"   {news['summary']}\n"
            report += "\n"
    else:
        report += "暂无新闻\n"
    
    report += """---

## 💡 【明日操作策略】

"""
    
    avg_change = sum(idx.get('change', 0) for idx in indices) / len(indices) if indices else 0
    
    if avg_change > 1:
        report += f"""**大盘强势（{avg_change:+.2f}%）**，明日预期：
- 可适当加大仓位，选择强势股
- 关注涨停股明日溢价机会
- 设置动态止盈位
"""
    elif avg_change > 0:
        report += f"""**大盘温和（{avg_change:+.2f}%）**，明日预期：
- 保持5-6成仓位
- 关注精选股票的回调机会
- 严格止损，不恋战
"""
    elif avg_change > -1:
        report += f"""**大盘震荡（{avg_change:+.2f}%）**，明日预期：
- 控制仓位3-5成
- 精选个股，轻仓试盘
- 等待企稳信号
"""
    else:
        report += f"""**大盘偏弱（{avg_change:+.2f}%）**，明日预期：
- 轻仓观望1-3成
- 不追高，等待买点
- 严格止损
"""

    if selected:
        report += f"""

**精选股票池**：{', '.join([s['stock']['name'] for s in selected[:3]])}
- 重点关注回调买点
- 单只仓位不超过2成
"""

    report += """

---

*本报告由量化模型自动分析，数据来源东方财富实时行情*
*投资有风险，模型仅供参考，不构成投资建议*
"""
    
    return report

def send_dingtalk(message):
    timestamp = get_timestamp()
    sign = generate_sign(timestamp, DINGTALK_SECRET)
    url = f"https://oapi.dingtalk.com/robot/send?access_token={DINGTALK_TOKEN}&timestamp={timestamp}&sign={sign}"
    headers = {'Content-Type': 'application/json'}
    data = {"msgtype": "markdown", "markdown": {"title": "量化精选早报", "text": message}}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=15)
        result = response.json()
        if result.get('errcode') == 0:
            print("✅ 钉钉消息发送成功!")
            return True
        else:
            print(f"❌ 发送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ 发送异常: {e}")
        return False

def main():
    print("=" * 60)
    print("📊 量化精选早报 - 开始运行")
    print("=" * 60)
    
    report = generate_report()
    print(f"📝 早报已生成，长度: {len(report)} 字符")
    
    success = send_dingtalk(report)
    
    if success:
        print("🎉 今日早报推送完成!")
    else:
        print("💥 推送失败")
    
    return success

if __name__ == "__main__":
    main()
