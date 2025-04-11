# import openai  # 注释掉OpenAI导入
import requests
import json
import logging
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
        # 根据爬取的数据构造AI提示
        # 这里需要根据具体数据结构定制
        return f"以下是来自{scraped_data['source']}的内容:\n\n{scraped_data['data']}\n\n请提取关键信息并总结。" 