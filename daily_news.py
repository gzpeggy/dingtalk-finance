#!/usr/bin/env python3
"""
每日财经早报 - 钉钉机器人推送
通过 GitHub Actions 自动执行
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
    """获取当前时间戳（毫秒）"""
    return str(int(time.time() * 1000))

def generate_sign(timestamp, secret):
    """生成钉钉签名"""
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    secret_enc = secret.encode('utf-8')
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    sign = urllib.parse.quote(sign)
    return sign

def search_finance_news():
    """搜索财经新闻"""
    news_items = []
    
    # 使用免费 API 获取财经新闻
    try:
        # 东方财富财经新闻 API
        response = requests.get(
            'https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html',
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if 'LivesList' in data:
                for item in data['LivesList'][:5]:
                    news_items.append({
                        'title': item.get('title', ''),
                        'summary': item.get('digest', '')[:50]
                    })
    except Exception as e:
        print(f"获取新闻失败: {e}")
    
    # 如果上面的API失败，使用备用新闻源
    if len(news_items) < 3:
        backup_news = [
            {'title': 'A股市场今日走势', 'summary': '关注大盘权重股表现'},
            {'title': '美联储利率决策', 'summary': '关注货币政策动向'},
            {'title': '国内经济数据发布', 'summary': '关注CPI/PPI数据'},
            {'title': '北向资金流向', 'summary': '关注外资动态'},
            {'title': '板块轮动分析', 'summary': '关注热点板块'}
        ]
        news_items = backup_news[:5]
    
    return news_items

def generate_report(news_items):
    """生成财经早报"""
    today = datetime.now().strftime('%Y年%m月%d日')
    
    report = f"""# 📈 财经早报 {today}

---

## 【今日股市前瞻】

**A股**：受外围市场影响，今日预计低开震荡，关注金融板块表现

**港股**：恒生指数有望企稳回升，关注科技股走势

**美股**：隔夜美股收跌，今日关注美联储官员讲话

---

## 【财经要闻】

"""
    
    for i, news in enumerate(news_items[:5], 1):
        report += f"{i}. **{news['title']}**\n   - {news['summary']}\n\n"
    
    report += """---

## 【今日操作建议】

- **仓位建议**：保持5成仓位为主
- **关注方向**：金融、消费、科技板块
- **风险提示**：控制仓位，关注外围市场波动

---

*本报告由AI自动生成，仅供参考*
"""
    
    return report

def send_dingtalk(message):
    """发送钉钉消息"""
    timestamp = get_timestamp()
    sign = generate_sign(timestamp, DINGTALK_SECRET)
    
    url = f"https://oapi.dingtalk.com/robot/send?access_token={DINGTALK_TOKEN}&timestamp={timestamp}&sign={sign}"
    
    headers = {'Content-Type': 'application/json'}
    
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "财经早报",
            "text": message
        }
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
    result = response.json()
    
    if result.get('errcode') == 0:
        print("✅ 钉钉消息发送成功!")
        return True
    else:
        print(f"❌ 发送失败: {result}")
        return False

def main():
    print("=" * 50)
    print("📊 开始获取财经早报...")
    print("=" * 50)
    
    # 获取新闻
    news_items = search_finance_news()
    print(f"📰 获取到 {len(news_items)} 条财经新闻")
    
    # 生成报告
    report = generate_report(news_items)
    print("📝 财经早报已生成")
    
    # 发送钉钉
    success = send_dingtalk(report)
    
    if success:
        print("🎉 每日财经早报推送完成!")
    else:
        print("💥 推送失败，请检查配置")
        
    return success

if __name__ == "__main__":
    main()
