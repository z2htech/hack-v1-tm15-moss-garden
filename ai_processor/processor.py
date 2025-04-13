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
        self.model = config["AI_MODEL"]  # 修改为字典访问方式
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
                "model": self.model,
                "messages": [
                    # {"role": "system", "content": "你是一个信息整合助手，请提取并总结以下信息的关键点:"},
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
    
    async def answer_question(self, user_query, tweets_data):
        """根据用户的问题和推文数据生成回答"""
        try:
            # 构建提示词
            prompt = self._prepare_question_prompt(user_query, tweets_data)
            
            # 构造DeepSeek API请求
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            # 发送请求到DeepSeek API
            response = requests.post(
                self.api_url,
                headers=headers,
                data=json.dumps(payload)
            )
            response.raise_for_status()
            response_data = response.json()
            
            # 提取AI回答
            answer = response_data["choices"][0]["message"]["content"]
            
            return answer
        except Exception as e:
            self.logger.error(f"AI回答问题失败: {str(e)}")
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

示例输出：
1. **整体市场情绪：**
   - 看多情绪 (Positive): 107 条
   - 中性情绪 (Neutral): 94 条
   - 看空情绪 (Negative): 57 条
   - 结论: *LONG*（看多情绪占优，107 > 57）

2. **分析理由：**
   - 看多情绪主要围绕比特币（$BTC）的潜在反转、特朗普政策（如关税豁免和“Trump Put”）对市场的积极影响，以及部分山寨币（如ETH、$HYPE）的短期机会
   - 中性情绪多为无关市场的个人动态或宏观政策讨论（如CPI、关税）
   - 看空情绪集中在市场操纵风险（如小市值代币）、安全漏洞（如Zoom通话导致的资产损失）以及对部分项目（如Fartcoin）的批评

3. **重要提示：**
   - 比特币（$BTC）：多位交易员认为贸易战和特朗普政策可能结束其下跌趋势
   - 山寨币机会：ETH、$HYPE等被提及有短期反弹或套利空间
   - 市场风险：需警惕小市值代币的庄家操纵和杠杆风险

4. **风险提示：**
   - 政治不确定性（如中美关税）可能引发波动
   - 小市值代币（如F3B）存在流动性陷阱和操纵风险
   - 安全风险（如钓鱼攻击通过Zoom会议）

5. **数据来源：**
   - 27位顶级交易员的Twitter推文（过去24小时）

"""
        
        return prompt
    
    def _prepare_question_prompt(self, user_query, tweets_data):
        """为用户问题准备提示词"""
        # 格式化推文数据为文本
        tweets_text = ""
        unique_traders = set()
        
        for i, tweet in enumerate(tweets_data, 1):
            trader_name = tweet.get("trader_name", "未知交易员")
            unique_traders.add(trader_name)
            
            sentiment = tweet.get("sentiment", "未知")
            reason = tweet.get("sentiment_reason", "无")
            explanation = tweet.get("sentiment_explanation", "无")
            content = tweet.get("current_tweet_content", "无内容")
            
            tweets_text += f"--- 推文 #{i} ---\n"
            tweets_text += f"交易员: {trader_name}\n"
            tweets_text += f"情绪: {sentiment}\n"
            if "asset_involved" in tweet:
                tweets_text += f"相关资产: {tweet['asset_involved']}\n"
            tweets_text += f"推文内容: {content}\n"
            tweets_text += f"分析理由: {reason}\n"
            tweets_text += f"详细解释: {explanation}\n\n"
        
        # 创建AI提示
        prompt = f"""
你是一位专业的加密货币市场分析师，名为Moss_bot，负责分析顶级交易员的推文并回答用户问题。

以下是来自{len(unique_traders)}位顶级交易员最近24小时内发布的推文数据，包含他们的观点、情绪分析和解释。

用户问题: {user_query}

请根据以下推文数据回答用户的问题。如果问题与特定交易员有关，请重点分析该交易员的观点。如果问题是关于整体市场情绪或特定资产，请综合所有相关交易员的观点进行回答。

你的回答应该：
1. 直接回应用户的问题
2. 引用交易员的具体观点和分析作为支持
3. 提供有见解的市场分析
4. 总结关键点和可能的风险
5. 保持客观专业

推文数据:
{tweets_text}

示例输出：
根据提供的推文数据，多位顶级交易员对BTC潜在反转的原因进行了分析，以下是综合观点和关键依据：

1. 宏观政策催化反转
   - Andrew Kang（推文#4）指出，贸易战引发的市场恐慌（capitulation）与潜在的“特朗普看跌期权”（Trump Put）形成组合拳，可能终结BTC数月来的下跌趋势。他认为政治干预（如关税政策调整）会迫使市场流动性转向，推动BTC反转。
   - DonAlt（推文#59）补充称，特朗普政府可能因美债收益率上升而妥协于关税政策，若部分关税取消，将直接利好风险资产（如BTC），形成“up only”行情。

2. 市场情绪与资金流动
   - Joshua | MOZAIK（推文#86、#87）观察到，随着基金减少空头头寸和市场对贸易战担忧缓解，BTC的“不确定性溢价”下降，资金可能重新流入。他认为BTC已展现抗跌性（ equities下跌时BTC未跟跌），且若CPI数据向好，可能触发更强劲的上涨。
   - Pentoshi（推文#52）提到，极端FUD（恐惧、不确定、怀疑）时期常伴随暴力反弹，尽管反转周期可能需要数月，但当前BTC估值具有吸引力。

3. 技术面与周期信号
   - Nachi（推文#84）从波浪理论分析，认为BTC处于“第三浪”初期，突破关键阻力位（如11万美元）后可能加速冲高至12万美元，并强调Stoch RSI指标显示底部信号。
   - 0xSun（推文#126）指出山寨币总市值（TOTAL3）已反弹15%，历史显示BTC往往在山寨币企稳后接力上涨。

4. 风险提示
   - Huma（推文#132、#134）持谨慎态度，认为BTC短期内仍与美股高度相关，尚未脱离“风险资产”属性，需警惕流动性危机中所有资产同步下跌的风险。
   - sigma²（推文#119、#120）警告关税政策可能引发“膝跳式反弹”（knee-jerk pump），但若市场深度不足，反转或不可持续。

总结
关键驱动因素：  
- 政治政策转向（如关税缓和）  
- 市场情绪修复（空头平仓、FUD出清）  
- 技术面超卖反弹需求  

潜在风险：  
- 宏观不确定性（如CPI数据、地缘冲突）  
- BTC与美股相关性未脱钩  
- 短期流动性波动  

建议投资者关注政策动向及BTC能否有效突破关键阻力位，同时控制杠杆以应对波动。当前市场分歧较大，需结合自身风险偏好布局。
"""
        
        return prompt