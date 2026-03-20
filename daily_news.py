#!/usr/bin/env python3
"""
每日财经早报 - 量化交易专业版
数据来源：东方财富、腾讯财经
包含：大盘指数、热点股票、量化点评、专业操作建议、财经新闻
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
    secret_enc = secret.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return urllib.parse.quote(sign)

def get_market_index():
    indices = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    index_codes = {'sh000001': '上证指数', 'sz399001': '深证成指', 'sz399006': '创业板指', 'sh000300': '沪深300'}
    
    for code, name in index_codes.items():
        try:
            url = f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayhfq&param={code},day,,,5,qfq'
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                text = response.text
                start, end = text.find('="'), text.rfind('"')
                if start != -1 and end != -1:
                    data = json.loads(text[start+2:end])
                    if 'data' in data and code in data['data']:
                        days = data['data'][code]['qfqday']
                        if len(days) >= 5:
                            latest = days[-1]
                            close_today = float(latest[1])
                            close_yesterday = float(latest[2])
                            ma5 = sum(float(d[1]) for d in days[-5:]) / 5
                            change_pct = (close_today - close_yesterday) / close_yesterday * 100 if close_yesterday != 0 else 0
                            indices.append({
                                'name': name, 'price': round(close_today, 2),
                                'change_pct': round(change_pct, 2), 'ma5': round(ma5, 2)
                            })
        except Exception as e:
            print(f"获取{name}失败: {e}")
    
    print(f"✅ 获取到 {len(indices)} 个指数")
    return indices

def get_hot_stocks():
    stocks = []
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'}
    
    try:
        url = 'https://push2.eastmoney.com/api/qt/clist/get'
        params = {'pn': 1, 'pz': 12, 'po': 1, 'np': 1, 'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                  'fltt': 2, 'invt': 2, 'fid': 'f3',
                  'fs': 'm:0+t:6,m:0+t:13,m:0+t:80,m:1+t:23,m:1+t:81',
                  'fields': 'f2,f3,f4,f5,f6,f7,f8,f10,f12,f14,f15,f16,f17,f18'}
        response = requests.get(url, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'diff' in data['data']:
                for item in data['data']['diff'][:12]:
                    stocks.append({
                        'name': item.get('f14', '未知'), 'code': item.get('f12', ''),
                        'price': item.get('f2', 0), 'change_pct': item.get('f3', 0),
                        'change_amt': item.get('f4', 0), 'volume': item.get('f5', 0),
                        'amount': item.get('f6', 0), 'amplitude': item.get('f7', 0),
                        'turnover': item.get('f8', 0), 'pe': item.get('f10', 0),
                        'high': item.get('f15', 0), 'low': item.get('f16', 0)
                    })
                print(f"✅ 获取到 {len(stocks)} 只涨幅榜股票")
                return stocks
    except Exception as e:
        print(f"获取热点股票失败: {e}")
    return []

def get_decline_stocks():
    stocks = []
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'}
    
    try:
        url = 'https://push2.eastmoney.com/api/qt/clist/get'
        params = {'pn': 1, 'pz': 8, 'po': 0, 'np': 1, 'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                  'fltt': 2, 'invt': 2, 'fid': 'f3',
                  'fs': 'm:0+t:6,m:0+t:13,m:0+t:80,m:1+t:23,m:1+t:81',
                  'fields': 'f2,f3,f5,f6,f7,f8,f10,f12,f14,f15,f16'}
        response = requests.get(url, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'diff' in data['data']:
                for item in data['data']['diff'][:8]:
                    stocks.append({
                        'name': item.get('f14', '未知'), 'code': item.get('f12', ''),
                        'price': item.get('f2', 0), 'change_pct': item.get('f3', 0),
                        'volume': item.get('f5', 0), 'amount': item.get('f6', 0),
                        'turnover': item.get('f8', 0), 'pe': item.get('f10', 0),
                        'high': item.get('f15', 0), 'low': item.get('f16', 0)
                    })
                print(f"✅ 获取到 {len(stocks)} 只跌幅榜股票")
                return stocks
    except Exception as e:
        print(f"获取跌幅榜失败: {e}")
    return []

def get_finance_news():
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
                        'summary': item.get('digest', '')[:50] if item.get('digest') else ''
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

def quantitative_analysis(stock):
    change = stock.get('change_pct', 0)
    turnover = stock.get('turnover', 0)
    amplitude = stock.get('amplitude', 0)
    pe = stock.get('pe', 0)
    high = stock.get('high', 0)
    low = stock.get('low', 0)
    
    signals = []
    risk_level = "中"
    action = "观望"
    
    # 涨停分析
    if change >= 9.9:
        if turnover > 20:
            signals.append("换手率极高，主力筹码松动")
            risk_level = "高"
            action = "谨慎追板，获利了结"
        elif turnover > 10:
            signals.append("换手率较高，封板资金活跃")
            risk_level = "中"
            action = "可持仓，设止盈"
        else:
            signals.append("封板坚决，筹码稳定")
            risk_level = "低"
            action = "继续持有"
    elif change >= 7:
        if turnover > 15:
            signals.append("高位放量，警惕出货")
            risk_level = "高"
            action = "逢高减仓"
        elif amplitude > 10:
            signals.append("振幅较大，多空博弈激烈")
            risk_level = "中"
            action = "高抛低吸"
        else:
            signals.append("量价齐升，趋势健康")
            risk_level = "低"
            action = "持有或低吸"
    elif change >= 4:
        if turnover > 10:
            signals.append("活跃度高，资金关注")
            risk_level = "中低"
            action = "可轻仓介入"
        else:
            signals.append("稳步上涨，趋势完好")
            risk_level = "低"
            action = "持有"
    elif change >= 2:
        signals.append("温和放量，稳步推升")
        risk_level = "低"
        action = "逢低加仓"
    elif change > 0:
        signals.append("小幅波动，方向不明")
        risk_level = "中"
        action = "观望等待"
    elif change <= -7:
        if turnover > 15:
            signals.append("放量下跌，资金出逃")
            risk_level = "极高"
            action = "严格止损"
        else:
            signals.append("恐慌抛售，超卖信号")
            risk_level = "高"
            action = "不抄底，等企稳"
    elif change <= -4:
        signals.append("明显破位，趋势走弱")
        risk_level = "高"
        action = "减仓止损"
    elif change <= -2:
        signals.append("小幅回调，注意支撑")
        risk_level = "中"
        action = "设止损持有"
    else:
        signals.append("窄幅震荡，等待突破")
        risk_level = "中"
        action = "观望"
    
    # 估值
    valuation = ""
    try:
        pe_val = float(pe) if pe and pe != '-' else 0
        if pe_val > 0:
            if pe_val < 15: valuation = "低估值"
            elif pe_val < 40: valuation = "合理"
            else: valuation = "高估值"
    except: pass
    
    # 技术位
    try:
        support = round(float(low) * 0.98, 2) if low else 0
        resist = round(float(high) * 1.01, 2) if high else 0
    except:
        support, resist = 0, 0
    
    return {
        'signals': signals, 'risk_level': risk_level, 'action': action,
        'valuation': valuation, 'support': support, 'resist': resist,
        'turnover': turnover, 'amplitude': amplitude
    }

def generate_report():
    today = datetime.now().strftime('%Y年%m月%d日 %H:%M')
    print("=" * 60)
    print("📊 量化交易早报 - 开始获取数据...")
    print("=" * 60)
    
    indices = get_market_index()
    hot_stocks = get_hot_stocks()
    decline_stocks = get_decline_stocks()
    news_list = get_finance_news()
    
    report = f"""# 📊 量化交易早报

**{today}**

---

## 【大盘指数】

"""
    
    if indices:
        for idx in indices:
            trend = '🔺' if idx['change_pct'] > 0 else '🔻' if idx['change_pct'] < 0 else '➡️'
            ma_signal = " MA5上方" if idx['price'] > idx['ma5'] else " MA5下方"
            report += f"**{idx['name']}**：{idx['price']} {trend} {idx['change_pct']:+.2f}%{ma_signal}\n"
        rise_count = len([s for s in hot_stocks if s.get('change_pct', 0) > 0])
        report += f"\n> 市场情绪：偏热 ({rise_count}只涨停或大涨)\n"
    else:
        report += "暂无实时数据\n"
    
    report += """---

## 🔥 【涨幅榜量化分析】

"""
    
    if hot_stocks:
        for i, stock in enumerate(hot_stocks[:8], 1):
            analysis = quantitative_analysis(stock)
            risk_emoji = {"低": "🟢", "中": "🟡", "中低": "🟢", "高": "🟠", "极高": "🔴"}.get(analysis['risk_level'], "🟡")
            report += f"**{i}. {stock['name']}** ({stock['code']})\n"
            report += f"   价格：¥{stock['price']} | 涨幅：🔺 **{stock['change_pct']:+.2f}%**\n"
            report += f"   换手率：{analysis['turnover']:.2f}% | 振幅：{analysis['amplitude']:.2f}%\n"
            report += f"   成交额：{format_amount(stock.get('amount', 0))}\n"
            if analysis['valuation']: report += f"   估值：{analysis['valuation']}\n"
            report += f"   量化信号：{' | '.join(analysis['signals'])}\n"
            report += f"   风险等级：{risk_emoji} {analysis['risk_level']}\n"
            if analysis['support'] and analysis['resist']:
                report += f"   技术位：支撑 {analysis['support']} | 压力 {analysis['resist']}\n"
            report += f"   **{analysis['action']}**\n\n"
    else:
        report += "暂无数据\n"
    
    report += """---

## 🔻 【跌幅榜风险提示】

"""
    
    if decline_stocks:
        for i, stock in enumerate(decline_stocks[:5], 1):
            analysis = quantitative_analysis(stock)
            risk_emoji = {"低": "🟢", "中": "🟡", "中低": "🟢", "高": "🟠", "极高": "🔴"}.get(analysis['risk_level'], "🟡")
            report += f"**{i}. {stock['name']}** ({stock['code']})\n"
            report += f"   价格：¥{stock['price']} | 跌幅：🔻 **{stock['change_pct']:.2f}%**\n"
            report += f"   换手率：{analysis['turnover']:.2f}%\n"
            report += f"   量化信号：{' | '.join(analysis['signals'])}\n"
            report += f"   风险等级：{risk_emoji} {analysis['risk_level']}\n"
            report += f"   **{analysis['action']}**\n\n"
    else:
        report += "暂无数据\n"
    
    report += """---

## 📰 【财经要闻】

"""
    
    if news_list:
        for i, news in enumerate(news_list[:8], 1):
            report += f"**{i}. {news['title']}**\n"
            if news['summary']: report += f"   {news['summary']}\n"
            report += "\n"
    else:
        report += "暂无新闻\n"
    
    report += """---

## 💡 【量化操作建议】

**仓位管理**：
- 总仓位建议：5-6成
- 热门板块仓位：≤2成
- 止损线：-3%严格执行

**选股策略**：
- 优先：换手率5-15%、涨幅3-7%的放量突破股
- 回避：换手率>25%的加速赶顶股
- 关注：量比>2、股价站在5日均线上方

**操作节奏**：
- 买入：回调至支撑位缩量时介入
- 卖出：放量滞涨或破5日线离场
- 持币：指数跌破20日均线时降仓

**风险控制**：
- 单只股票仓位≤20%
- 亏损超过5%必须止损
- 避免盲目追涨停板

---

*本报告由量化模型自动生成，数据来源东方财富/腾讯财经*
*投资有风险，模型仅供参考，不构成投资建议*
"""
    return report

def send_dingtalk(message):
    timestamp = get_timestamp()
    sign = generate_sign(timestamp, DINGTALK_SECRET)
    url = f"https://oapi.dingtalk.com/robot/send?access_token={DINGTALK_TOKEN}&timestamp={timestamp}&sign={sign}"
    headers = {'Content-Type': 'application/json'}
    data = {"msgtype": "markdown", "markdown": {"title": "量化交易早报", "text": message}}
    
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
    print("📊 量化交易早报 - 开始运行")
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

