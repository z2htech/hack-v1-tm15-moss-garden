import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime
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
    
    def scrape_website(self, website_config):
        try:
            url = website_config["url"]
            self.logger.info(f"开始爬取: {url}")
            
            # 使用Selenium获取动态内容
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.get(url)
            
            # 等待页面加载完成
            self.logger.info("等待页面内容加载...")
            time.sleep(5)  # 等待动态内容加载
            
            try:
                # 尝试等待主要内容加载
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "main-content"))
                )
            except Exception as e:
                self.logger.warning(f"等待特定元素超时，将继续使用当前页面: {str(e)}")
            
            # 获取页面内容
            html_content = driver.page_source
            driver.quit()
            
            # 使用BeautifulSoup解析获取的HTML
            soup = BeautifulSoup(html_content, "html.parser")
            # 解析具体内容
            data = self._parse_xgpt_data(soup, website_config)
            
            return {
                "source": website_config["name"],
                "url": url,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"爬取失败: {url}, 错误: {str(e)}")
            return None
    
    def _parse_data(self, soup, website_config):
        # 通用解析器，根据网站类型选择不同的专用解析器
        if "x-gpt.bwequation.com" in website_config["url"]:
            return self._parse_xgpt_data(soup, website_config)
        else:
            # 默认解析逻辑
            self.logger.warning(f"没有针对 {website_config['url']} 的专用解析器，将使用默认解析")
            return "无法解析网站内容，请为此网站创建专用解析器。"
    
    def _parse_xgpt_data(self, soup, website_config):
        """专门解析x-gpt.bwequation.com网站的数据"""
        self.logger.info("使用x-gpt解析器")
        
        # 提取所有推文
        tweets = []
        
        # 保存页面内容以供调试
        with open("page_content.html", "w", encoding="utf-8") as f:
            f.write(str(soup))
        self.logger.info("已将页面内容保存到 page_content.html 文件中")
        
        # 尝试查找推文容器 - 单页应用可能有不同的DOM结构
        tweet_containers = soup.find_all("div", class_=lambda c: c and any(x in c for x in ["tweet", "post", "card"]))
        
        if not tweet_containers:
            # 第二种尝试 - 查找可能包含推文的区域
            tweet_containers = soup.find_all("div", attrs={"style": lambda s: s and "margin" in s})
        
        if not tweet_containers:
            # 第三种尝试 - 查找所有可能是文章或推文的div
            tweet_containers = soup.find_all("div", attrs={"role": "article"})
        
        self.logger.info(f"找到可能的推文容器: {len(tweet_containers)}个")
        
        # 如果仍然找不到，尝试通过文本内容查找
        if not tweet_containers:
            # 查找包含"Asset Involved"或者"Reason"等关键词的元素
            asset_tags = soup.find_all(text=re.compile(r"Asset\s+Involved|positive|negative|Reason"))
            if asset_tags:
                self.logger.info(f"通过关键词找到可能的标签: {len(asset_tags)}个")
                for tag in asset_tags:
                    # 向上找到可能的容器
                    potential_container = self._find_parent_container(tag)
                    if potential_container and potential_container not in tweet_containers:
                        tweet_containers.append(potential_container)
        
        # 通过文本分析提取推文
        for container in tweet_containers:
            try:
                # 提取所有文本，按行分割
                container_text = container.get_text(separator="\n").strip()
                
                # 构建一个基本结构
                tweet = {
                    "trader": "未知交易员",
                    "content": "",
                    "asset": "未知资产",
                    "sentiment": "未知情绪",
                    "reason": "未知原因",
                    "explanation": "未知解释",
                    "time": "未知时间"
                }
                
                # 通过文本分析提取信息
                lines = container_text.split("\n")
                current_section = None
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 尝试确定行的内容类型
                    if re.search(r'@\w+', line):  # 用户名模式
                        tweet["trader"] = line
                    elif "Asset Involved" in line:
                        current_section = "asset"
                    elif "positive" in line.lower() or "negative" in line.lower():
                        tweet["sentiment"] = line
                    elif "Reason" in line:
                        current_section = "reason"
                    elif "Explanation" in line:
                        current_section = "explanation"
                    elif re.search(r'\d+\s+minute', line) or re.search(r'\d+\s+hour', line):
                        tweet["time"] = line
                    elif current_section == "asset" and tweet["asset"] == "未知资产":
                        tweet["asset"] = line
                    elif current_section == "reason" and tweet["reason"] == "未知原因":
                        tweet["reason"] = line
                    elif current_section == "explanation" and tweet["explanation"] == "未知解释":
                        tweet["explanation"] = line
                    elif not current_section and tweet["content"] == "":
                        tweet["content"] = line
                
                tweets.append(tweet)
                
            except Exception as e:
                self.logger.error(f"解析推文时出错: {str(e)}")
        
        # 如果没有找到推文，使用替代方法
        if not tweets:
            self.logger.warning("未找到结构化推文，尝试提取所有文本")
            
            # 尝试提取可能包含交易信息的文本块
            trade_sections = []
            all_paragraphs = soup.find_all(["p", "div"], class_=lambda c: c and "text" in str(c).lower())
            
            for para in all_paragraphs:
                text = para.get_text().strip()
                if len(text) > 50:  # 只考虑长度合理的文本块
                    trade_sections.append(text)
            
            # 如果找到可能的交易信息文本，返回这些文本
            if trade_sections:
                return "交易信息摘要:\n\n" + "\n\n".join(trade_sections)
            else:
                # 如果仍然没有找到，提取整个页面的文本
                all_text = soup.get_text(separator="\n", strip=True)
                return f"未能提取结构化数据，以下是页面文本:\n\n{all_text[:5000]}..."
        
        # 将推文数据格式化为字符串
        formatted_data = "交易信息汇总:\n\n"
        for i, tweet in enumerate(tweets, 1):
            formatted_data += f"--- 推文 #{i} ---\n"
            formatted_data += f"交易员: {tweet['trader']}\n"
            formatted_data += f"内容: {tweet['content']}\n"
            formatted_data += f"资产: {tweet['asset']}\n"
            formatted_data += f"情绪: {tweet['sentiment']}\n"
            formatted_data += f"原因: {tweet['reason']}\n"
            formatted_data += f"解释: {tweet['explanation']}\n"
            formatted_data += f"时间: {tweet['time']}\n\n"
        
        return formatted_data
    
    def _find_parent_container(self, tag, max_levels=5):
        """向上查找可能的容器元素"""
        current = tag
        for _ in range(max_levels):
            if current.parent:
                current = current.parent
                # 检查这个父元素是否可能是容器
                if current.name == "div" and (current.get("class") or current.get("id")):
                    return current
        return None 