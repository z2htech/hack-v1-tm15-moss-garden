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
            for trader in traders_data:  # 先爬取前3个交易员作为测试
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
            
            # 解决点击拦截问题：先滚动到元素位置
            try:
                # 方法1: 使用JavaScript滚动到元素位置
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", trader['element'])
                time.sleep(1)  # 等待滚动完成
                
                # 方法2: 如果直接点击仍然被拦截，使用JavaScript执行点击
                try:
                    trader['element'].click()
                except Exception as e:
                    self.logger.warning(f"直接点击失败，尝试使用JavaScript点击: {str(e)}")
                    self.driver.execute_script("arguments[0].click();", trader['element'])
            except Exception as e:
                self.logger.error(f"滚动到元素位置失败: {str(e)}")
                # 尝试最后的方法 - 直接点击
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
                
                # 过滤最近24小时内的推文
                recent_tweets = self.filter_recent_tweets(tweets_data)
                
                self.logger.info(f"成功获取到 {trader['name']} 的 {len(recent_tweets)} 条最近24小时内的推文")
                
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
        
        # 查找所有推文容器
        tweet_containers = soup.find_all("div", class_="tweet-container")
        
        for i, container in enumerate(tweet_containers):
            try:
                tweet_data = {}
                
                # 从JSON元素中提取基本信息（如果有）
                if i < len(json_elements):
                    try:
                        json_text = json_elements[i].get_text(strip=True)
                        if json_text.startswith("{") and json_text.endswith("}"):
                            tweet_data = json.loads(json_text)
                    except Exception as e:
                        self.logger.error(f"解析JSON数据失败: {str(e)}")
                
                # 添加交易员名称
                tweet_data["trader_name"] = trader_name
                
                # 查找情绪标签容器
                sentiment_container = container.find("div", class_=lambda c: c and c.startswith("tweet-gpt-sentiment-"))
                if sentiment_container:
                    # 确定情绪类型（positive/neutral/negative）
                    sentiment_class = sentiment_container.get("class", [])
                    sentiment_type = ""
                    for cls in sentiment_class:
                        if cls.startswith("tweet-gpt-sentiment-"):
                            sentiment_type = cls.replace("tweet-gpt-sentiment-", "")
                            break
                    
                    # 提取情绪标签
                    sentiment_tag = sentiment_container.find("span", class_="el-tag__content")
                    if sentiment_tag:
                        tweet_data["sentiment"] = sentiment_tag.get_text(strip=True)
                    else:
                        tweet_data["sentiment"] = sentiment_type
                    
                    # 提取资产信息
                    asset_span = sentiment_container.find("span", string=lambda s: s and "Asset Involved:" in s)
                    if asset_span:
                        asset_text = asset_span.get_text(strip=True).replace("Asset Involved:", "").strip()
                        if asset_text:
                            tweet_data["asset_involved"] = asset_text
                    
                    # 提取原因(Reason)
                    reason_span = sentiment_container.find("span", class_="tweet-gpt-res-filed", string=lambda s: s and "Reason:" in s)
                    if reason_span:
                        reason_text = reason_span.find_next("span", class_=["text", "text-link"])
                        if reason_text:
                            tweet_data["sentiment_reason"] = reason_text.get_text(strip=True)
                    
                    # 提取解释(Explanation)
                    explanation_span = sentiment_container.find("span", class_="tweet-gpt-res-filed", string=lambda s: s and "Explanation:" in s)
                    if explanation_span:
                        explanation_text = explanation_span.find_next("span", class_=["text", "text-link"])
                        if explanation_text:
                            tweet_data["sentiment_explanation"] = explanation_text.get_text(strip=True)
                
                # 确保推文的基本内容被保留
                if 'tweet_username' not in tweet_data:
                    # 尝试从页面提取用户名
                    username_element = container.find("span", class_="name")
                    screen_name_element = container.find("span", class_="screen-name")
                    time_element = container.find("span", class_="nav-time")
                    
                    if username_element and screen_name_element and time_element:
                        username = username_element.get_text(strip=True)
                        screen_name = screen_name_element.get_text(strip=True)
                        time_text = time_element.get_text(strip=True)
                        tweet_data["tweet_username"] = f"{username} ({screen_name}) Posted on {time_text}"
                
                if 'current_tweet_content' not in tweet_data:
                    # 尝试从页面提取推文内容
                    tweet_text_element = container.find("div", class_=["tweet-text", "text", "text-link"])
                    if tweet_text_element:
                        tweet_data["current_tweet_content"] = tweet_text_element.get_text(strip=True)
                
                if 'picture_included' not in tweet_data:
                    # 检查是否包含图片
                    image_gallery = container.find("div", class_="image-gallery")
                    if image_gallery:
                        tweet_data["picture_included"] = True
                        # 提取图片URL
                        image_elements = image_gallery.find_all("img", class_="el-image__inner")
                        if image_elements and 'picture_urls' not in tweet_data:
                            tweet_data["picture_urls"] = [img.get("src") for img in image_elements if img.get("src")]
                    else:
                        tweet_data["picture_included"] = False
                        tweet_data["picture_urls"] = []
                
                tweets.append(tweet_data)
            except Exception as e:
                self.logger.error(f"处理推文容器失败: {str(e)}")
        
        # 如果上述方法没有找到任何推文，尝试使用正则表达式直接从页面中提取
        if not tweets:
            try:
                # 使用正则表达式查找所有JSON格式的文本
                json_pattern = r'(\{[\s\S]*?"tweet_username"[\s\S]*?\})'
                matches = re.findall(json_pattern, page_source)
                
                for match in matches:
                    try:
                        tweet_data = json.loads(match)
                        tweet_data["trader_name"] = trader_name
                        
                        # 尝试从页面中提取情感信息
                        try:
                            # 使用正则表达式查找情感标签、原因和解释
                            sentiment_pattern = r'<span class="el-tag__content">([^<]+)</span>'
                            reason_pattern = r'<span class="tweet-gpt-res-filed">Reason:</span><span class="text(?:-link)?">([^<]+)</span>'
                            explanation_pattern = r'<span class="tweet-gpt-res-filed">Explanation:</span><span class="text(?:-link)?">([^<]+)</span>'
                            asset_pattern = r'<span[^>]*>Asset Involved: ([^<]+)</span>'
                            
                            sentiment_matches = re.findall(sentiment_pattern, page_source)
                            reason_matches = re.findall(reason_pattern, page_source)
                            explanation_matches = re.findall(explanation_pattern, page_source)
                            asset_matches = re.findall(asset_pattern, page_source)
                            
                            if sentiment_matches and len(sentiment_matches) > 0:
                                for sentiment in sentiment_matches:
                                    if sentiment in ["positive", "neutral", "negative"]:
                                        tweet_data["sentiment"] = sentiment
                                        break
                            
                            if reason_matches and len(reason_matches) > 0:
                                tweet_data["sentiment_reason"] = reason_matches[0]
                            
                            if explanation_matches and len(explanation_matches) > 0:
                                tweet_data["sentiment_explanation"] = explanation_matches[0]
                            
                            if asset_matches and len(asset_matches) > 0:
                                tweet_data["asset_involved"] = asset_matches[0]
                        except Exception as e:
                            self.logger.error(f"使用正则表达式提取情感信息失败: {str(e)}")
                        
                        tweets.append(tweet_data)
                    except:
                        pass
            except Exception as e:
                self.logger.error(f"使用正则表达式提取JSON失败: {str(e)}")
        
        return tweets
    
    def filter_recent_tweets(self, tweets_data):
        """过滤最近24小时内的推文"""
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
                is_within_24_hours = False
                
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
                
                # 检查是否在最近24小时内
                if tweet_time:
                    is_within_24_hours = (current_time - tweet_time) <= timedelta(hours=24)
                    tweet["parsed_time"] = tweet_time.isoformat()
                    tweet["is_recent"] = is_within_24_hours
                else:
                    # 如果无法解析时间，默认保留该推文（保守策略）
                    is_within_24_hours = True
                    tweet["parsed_time"] = "unknown"
                    tweet["is_recent"] = True
                
                if is_within_24_hours:
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
            return "未找到最近24小时内的推文"
        
        formatted_data = "交易信息汇总 (最近24小时):\n\n"
        for i, tweet in enumerate(tweets, 1):
            formatted_data += f"--- 推文 #{i} ---\n"
            formatted_data += f"交易员: {tweet.get('trader_name', '未知')}\n"
            
            # 用户名和发布时间
            if "tweet_username" in tweet:
                formatted_data += f"推特: {tweet['tweet_username']}\n"
            
            # 推文内容
            if "current_tweet_content" in tweet:
                formatted_data += f"内容: {tweet['current_tweet_content']}\n"
            
            # 直接从网页提取的情绪信息
            if "sentiment" in tweet:
                formatted_data += f"情绪: {tweet['sentiment']}\n"
            
            if "sentiment_reason" in tweet:
                formatted_data += f"原因: {tweet['sentiment_reason']}\n"
                
            if "sentiment_explanation" in tweet:
                formatted_data += f"解释: {tweet['sentiment_explanation']}\n"
            
            # 资产信息
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