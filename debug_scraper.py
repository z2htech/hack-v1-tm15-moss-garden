import logging
from config.config import *
from scraper.scraper import WebScraper

# 设置基本日志
logging.basicConfig(level=logging.INFO)

def main():
    # 创建爬虫
    scraper = WebScraper(config={
        "TELEGRAM_API_TOKEN": TELEGRAM_API_TOKEN,
        "DEEPSEEK_API_KEY": DEEPSEEK_API_KEY,
        "AI_MODEL": AI_MODEL,
        "AI_TEMPERATURE": AI_TEMPERATURE,
        "DEEPSEEK_API_URL": DEEPSEEK_API_URL
    })
    
    # 爬取测试
    result = scraper.scrape_website({
        "name": "X-GPT交易",
        "url": "https://x-gpt.bwequation.com/",
        "update_frequency": 3600
    })
    
    if result:
        print("\n获取的数据:")
        print(result["data"])
    else:
        print("爬取失败")

if __name__ == "__main__":
    main() 