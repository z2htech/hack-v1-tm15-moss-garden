# import openai  # 注释掉OpenAI导入
import requests
import json
import logging
import re
from datetime import datetime

class AIProcessor:
    def __init__(self, config):
        self.config = config
        # openai.api_key = config.OPENAI_API_KEY  # 注释掉OpenAI配置
        self.api_key = config["DEEPSEEK_API_KEY"]  # 修改为字典访问方式
        self.api_url = config["DEEPSEEK_API_URL"]  # 修改为字典访问方式
        self.logger = logging.getLogger("ai_processor")
    
    async def process_data(self, scraped_data):
        self.logger.info(f"处理来自 {scraped_data['source']} 的数据")
        
        try:
            # 准备发送给AI的提示
            prompt = self._prepare_prompt(scraped_data)
            print(scraped_data)
            
            # 调用DeepSeek API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": self.config["AI_MODEL"],  # 修改为字典访问方式
                "messages": [
                    {"role": "system", "content": "你是一个信息整合助手，请提取并总结以下信息的关键点:"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.config["AI_TEMPERATURE"]  # 修改为字典访问方式
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                data=json.dumps(payload)
            )
            response.raise_for_status()
            response_data = response.json()
            
            # 根据DeepSeek API的响应格式提取内容
            # 注意：这里的响应格式解析需要根据实际DeepSeek API返回格式调整
            summary = response_data["choices"][0]["message"]["content"]
            
            return {
                "original_data": scraped_data,
                "summary": summary,
                "processed_at": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"AI处理失败: {str(e)}")
            return None
    
    def _prepare_prompt(self, scraped_data):
        """根据爬取的数据构造AI提示"""
        
        # 创建一个计数器来统计不同情绪的推文数量
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        
        # 提取所有推文数据
        all_tweets = scraped_data.get("data", "")
        
        # 如果原始数据是字符串格式，尝试提取具体推文内容
        tweets_content = ""
        trader_count = 0
        unique_traders = set()
        
        # 从原始数据中提取推文
        if isinstance(all_tweets, str):
            # 已经是格式化的字符串
            tweets_content = all_tweets
            
            # 尝试统计交易员数量
            trader_matches = re.findall(r"交易员: ([^\n]+)", all_tweets)
            unique_traders = set(trader_matches)
            trader_count = len(unique_traders)
            
            # 尝试统计情绪
            positive_count = all_tweets.lower().count("positive")
            neutral_count = all_tweets.lower().count("neutral")
            negative_count = all_tweets.lower().count("negative")
            
            sentiment_counts["positive"] = positive_count
            sentiment_counts["neutral"] = neutral_count
            sentiment_counts["negative"] = negative_count
        
        # 构建AI提示
        prompt = f"""
你是一位专业的加密货币市场分析师，负责分析来自顶级交易员的Twitter发言，评估市场情绪倾向。

以下是来自{trader_count}位顶级交易员在过去24小时内发布的推文及其情绪分析。请基于这些数据，评估整体市场情绪是看多(LONG)、看空(SHORT)还是中性(NEUTRAL)，并提供详细的分析理由。

已统计情绪分布：
- 看多情绪(Positive): {sentiment_counts["positive"]} 条推文
- 中性情绪(Neutral): {sentiment_counts["neutral"]} 条推文
- 看空情绪(Negative): {sentiment_counts["negative"]} 条推文

请你整理分析这些数据，输出格式如下：

1. 整体市场情绪：[LONG/SHORT/NEUTRAL] (明确选择一种，如果positive多于negative则选择LONG，如果negative多于positive则选择SHORT，否则选择NEUTRAL)

2. 分析理由：(提供一段200-300字的综合分析，解释为什么得出这一结论，引用推文中{tweets_content}的explanation作为佐证)

3. 重要提示：(列出3-5点交易员们提到的市场关键点)

4. 风险提示：(根据推文中的警告，提供投资者应当注意的风险因素)

5. 最后不必要加入数据来源说明

原始推文数据：
{tweets_content}
"""
        
        return prompt