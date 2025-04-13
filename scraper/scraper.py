import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta
import json
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class WebScraper:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger("scraper")
        # 初始化Selenium选项
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")  # 无头模式，不显示浏览器
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--window-size=1920,1080")
        self.driver = None
    
    def __del__(self):
        # 确保退出时关闭driver
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def scrape_website(self, website_config):
        try:
            url = website_config["url"]
            self.logger.info(f"开始爬取: {url}")
            
            # 使用Selenium获取动态内容
            self.driver = webdriver.Chrome(options=self.chrome_options)
            self.driver.get(url)
            
            # 等待页面加载完成
            self.logger.info("等待页面内容加载...")
            time.sleep(5)  # 等待动态内容加载
            
            # 获取所有交易员
            traders_data = self.get_all_traders()
            
            all_tweets = []
            
            # 遍历每个交易员
            for trader in traders_data[:3]:  # 先爬取前3个交易员作为测试
                trader_tweets = self.scrape_trader_tweets(trader)
                all_tweets.extend(trader_tweets)
            
            # 关闭浏览器
            self.driver.quit()
            self.driver = None
            
            # 格式化推文数据为字符串
            formatted_data = self.format_tweets_data(all_tweets)
            
            # 保存提取的内容到文件
            with open("extracted_tweets.json", "w", encoding="utf-8") as f:
                json.dump(all_tweets, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"已爬取 {len(all_tweets)} 条推文并保存到 extracted_tweets.json")
            
            # ai解析的网页数据格式
            return {
                "source": website_config["name"],
                "url": url,
                "data": formatted_data,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"爬取失败: {url}, 错误: {str(e)}")
            if self.driver:
                self.driver.quit()
                self.driver = None
            return None
    
    def get_all_traders(self):
        """获取所有交易员列表"""
        try:
            # 尝试查找所有交易员元素
            trader_elements = self.driver.find_elements(By.CSS_SELECTOR, ".profile.user")
            
            if not trader_elements:
                self.logger.warning("未找到交易员元素，尝试其他选择器")
                trader_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-v-759468ba]")
            
            self.logger.info(f"找到 {len(trader_elements)} 个交易员")
            
            traders = []
            for element in trader_elements:
                try:
                    # 尝试获取交易员名称和Twitter用户名
                    name_element = element.find_element(By.CSS_SELECTOR, ".name")
                    screen_name_element = element.find_element(By.CSS_SELECTOR, ".screen-name a")
                    
                    name = name_element.text.strip() if name_element else "Unknown"
                    screen_name = screen_name_element.text.strip() if screen_name_element else ""
                    link = screen_name_element.get_attribute("href") if screen_name_element else ""
                    
                    trader_info = {
                        'element': element,
                        'name': name,
                        'screen_name': screen_name,
                        'link': link
                    }
                    traders.append(trader_info)
                    self.logger.info(f"添加交易员: {name} ({screen_name})")
                except Exception as e:
                    self.logger.error(f"获取交易员信息失败: {str(e)}")
            
            return traders
            
        except Exception as e:
            self.logger.error(f"获取交易员列表失败: {str(e)}")
            # 尝试截图保存页面，以便调试
            try:
                self.driver.save_screenshot('debug_traders_page.png')
                self.logger.info("已保存页面截图至 debug_traders_page.png")
            except:
                pass
            return []
    
    def scrape_trader_tweets(self, trader):
        """爬取指定交易员的推文"""
        try:
            # 点击交易员获取其推文
            self.logger.info(f"点击交易员: {trader['name']} ({trader['screen_name']})")
            trader['element'].click()
            
            # 等待推文加载
            time.sleep(3)
            
            # 保存页面以便调试
            page_source = self.driver.page_source
            with open(f"trader_{trader['name'].replace(' ', '_')}_page.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            
            # 获取所有推文数据
            try:
                # 直接从页面中提取推文JSON数据
                tweets_data = self.extract_tweets_json(page_source, trader['name'])
                
                # 过滤最近12小时内的推文
                recent_tweets = self.filter_recent_tweets(tweets_data)
                
                self.logger.info(f"成功获取到 {trader['name']} 的 {len(recent_tweets)} 条最近12小时内的推文")
                
                # 返回到交易员列表页面
                try:
                    back_button = self.driver.find_element(By.CSS_SELECTOR, "button.el-icon.back-button")
                    back_button.click()
                    time.sleep(2)
                except:
                    # 如果找不到返回按钮，尝试点击"All Traders"
                    try:
                        all_traders_btn = self.driver.find_element(By.XPATH, "//h3[text()='All Traders']")
                        all_traders_btn.click()
                        time.sleep(2)
                    except:
                        # 仍然失败，尝试刷新页面回到主页
                        self.driver.get(self.config["WEBSITES"][0]["url"])
                        time.sleep(3)
                
                return recent_tweets
            
            except Exception as e:
                self.logger.error(f"提取或解析推文失败: {str(e)}")
                return []
            
        except Exception as e:
            self.logger.error(f"爬取交易员 {trader['name']} 的推文失败: {str(e)}")
            # 尝试返回到主页
            try:
                self.driver.get(self.config["WEBSITES"][0]["url"])
                time.sleep(3)
            except:
                pass
            return []
    
    def extract_tweets_json(self, page_source, trader_name):
        """从页面源码中提取推文JSON数据"""
        soup = BeautifulSoup(page_source, "html.parser")
        tweets = []
        
        # 查找包含JSON数据的元素
        json_elements = soup.find_all("div", attrs={"data-v-e54e3009": True})
        
        if not json_elements:
            # 如果没有找到指定的元素，尝试查找所有可能包含JSON的元素
            json_elements = soup.find_all("div", attrs={"style": "white-space: pre-wrap;"})
        
        self.logger.info(f"找到 {len(json_elements)} 个可能包含JSON数据的元素")
        
        for element in json_elements:
            try:
                # 获取JSON文本并解析
                json_text = element.get_text(strip=True)
                if json_text.startswith("{") and json_text.endswith("}"):
                    tweet_data = json.loads(json_text)
                    
                    # 检查是否为有效的推文数据
                    if "tweet_username" in tweet_data or "current_tweet_content" in tweet_data:
                        # 添加交易员名称
                        tweet_data["trader_name"] = trader_name
                        tweets.append(tweet_data)
            except Exception as e:
                self.logger.error(f"解析JSON数据失败: {str(e)}")
        
        # 如果上面的方法没有找到任何推文，尝试使用正则表达式直接从页面中提取
        if not tweets:
            try:
                # 使用正则表达式查找所有JSON格式的文本
                json_pattern = r'(\{[\s\S]*?"tweet_username"[\s\S]*?\})'
                matches = re.findall(json_pattern, page_source)
                
                for match in matches:
                    try:
                        tweet_data = json.loads(match)
                        tweet_data["trader_name"] = trader_name
                        tweets.append(tweet_data)
                    except:
                        pass
            except Exception as e:
                self.logger.error(f"使用正则表达式提取JSON失败: {str(e)}")
        
        return tweets
    
    def filter_recent_tweets(self, tweets_data):
        """过滤最近12小时内的推文"""
        current_time = datetime.now()
        recent_tweets = []
        
        for tweet in tweets_data:
            try:
                # 尝试从推文数据中提取时间信息
                time_info = ""
                if "tweet_username" in tweet:
                    # 通常格式为 "RunnerXBT (@RunnerXBT) Posted on 2025-04-12 22:17:35"
                    username_parts = tweet["tweet_username"].split("Posted on")
                    if len(username_parts) > 1:
                        time_info = username_parts[1].strip()
                
                # 如果没有在tweet_username中找到时间，查找其他可能的字段
                if not time_info and "timestamp" in tweet:
                    time_info = tweet["timestamp"]
                
                # 尝试解析时间
                tweet_time = None
                is_within_12_hours = False
                
                # 尝试不同的时间格式
                if time_info:
                    try:
                        # 尝试格式 "2025-04-12 22:17:35"
                        tweet_time = datetime.strptime(time_info, "%Y-%m-%d %H:%M:%S")
                    except:
                        try:
                            # 尝试带毫秒的格式
                            tweet_time = datetime.strptime(time_info, "%Y-%m-%d %H:%M:%S.%f")
                        except:
                            # 如果上述格式都失败，尝试查找相对时间描述
                            if "minute" in time_info or "hour" in time_info or "second" in time_info:
                                match = re.search(r'(\d+)\s+(minute|hour|second)s?\s+ago', time_info, re.IGNORECASE)
                                if match:
                                    number = int(match.group(1))
                                    unit = match.group(2).lower()
                                    
                                    if unit == 'second':
                                        tweet_time = current_time - timedelta(seconds=number)
                                    elif unit == 'minute':
                                        tweet_time = current_time - timedelta(minutes=number)
                                    elif unit == 'hour':
                                        tweet_time = current_time - timedelta(hours=number)
                
                # 检查是否在最近12小时内
                if tweet_time:
                    is_within_12_hours = (current_time - tweet_time) <= timedelta(hours=12)
                    tweet["parsed_time"] = tweet_time.isoformat()
                    tweet["is_recent"] = is_within_12_hours
                else:
                    # 如果无法解析时间，默认保留该推文（保守策略）
                    is_within_12_hours = True
                    tweet["parsed_time"] = "unknown"
                    tweet["is_recent"] = True
                
                if is_within_12_hours:
                    recent_tweets.append(tweet)
                
            except Exception as e:
                self.logger.error(f"过滤推文时间失败: {str(e)}")
                # 如果时间解析失败，默认保留该推文
                tweet["parsed_time"] = "error"
                tweet["is_recent"] = True
                recent_tweets.append(tweet)
        
        return recent_tweets
    
    def format_tweets_data(self, tweets):
        """将推文数据格式化为可读字符串"""
        if not tweets:
            return "未找到最近12小时内的推文"
        
        formatted_data = "交易信息汇总 (最近12小时):\n\n"
        for i, tweet in enumerate(tweets, 1):
            formatted_data += f"--- 推文 #{i} ---\n"
            formatted_data += f"交易员: {tweet.get('trader_name', '未知')}\n"
            
            # 用户名和发布时间
            if "tweet_username" in tweet:
                formatted_data += f"推特: {tweet['tweet_username']}\n"
            
            # 推文内容
            if "current_tweet_content" in tweet:
                formatted_data += f"内容: {tweet['current_tweet_content']}\n"
            
            # 情绪和资产信息 (如果有)
            sentiment = self.extract_sentiment(tweet)
            if sentiment:
                formatted_data += f"情绪: {sentiment}\n"
            
            assets = self.extract_assets(tweet)
            if assets:
                formatted_data += f"相关资产: {assets}\n"
            
            # 是否包含图片
            if tweet.get("picture_included", False):
                formatted_data += f"包含图片: 是\n"
                if "picture_urls" in tweet and tweet["picture_urls"]:
                    formatted_data += f"图片链接: {', '.join(tweet['picture_urls'])}\n"
            
            # 添加分隔行
            formatted_data += "\n"
        
        return formatted_data
    
    def extract_sentiment(self, tweet):
        """从推文中提取情绪信息"""
        content = tweet.get("current_tweet_content", "").lower()
        
        # 简单的情绪分析
        positive_words = ["bullish", "long", "buy", "uptrend", "moon", "pump", "positive", "good", "great", "excellent"]
        negative_words = ["bearish", "short", "sell", "downtrend", "dump", "negative", "bad", "poor", "terrible"]
        neutral_words = ["neutral", "sideways", "ranging", "consolidation"]
        
        positive_count = sum(1 for word in positive_words if word in content)
        negative_count = sum(1 for word in negative_words if word in content)
        neutral_count = sum(1 for word in neutral_words if word in content)
        
        if positive_count > negative_count and positive_count > neutral_count:
            return "看涨/积极"
        elif negative_count > positive_count and negative_count > neutral_count:
            return "看跌/消极"
        elif neutral_count > 0:
            return "中性/观望"
        else:
            return ""
    
    def extract_assets(self, tweet):
        """从推文中提取资产信息"""
        content = tweet.get("current_tweet_content", "")
        
        # 查找常见加密货币符号
        crypto_pattern = r'(\$[A-Z]{2,5})'
        matches = re.findall(crypto_pattern, content)
        
        if matches:
            return ", ".join(matches)
        
        # 查找常见加密货币名称
        common_cryptos = ["Bitcoin", "Ethereum", "ETH", "BTC", "XRP", "Solana", "SOL", "Dogecoin", "DOGE"]
        found_cryptos = [crypto for crypto in common_cryptos if crypto in content or crypto.lower() in content]
        
        if found_cryptos:
            return ", ".join(found_cryptos)
        
        return ""