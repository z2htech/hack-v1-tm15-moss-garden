# API密钥和配置
TELEGRAM_API_TOKEN = ""
DEEPSEEK_API_KEY = ""  # 添加DeepSeek API密钥

# 爬虫配置
WEBSITES = [
    {
        "name": "示例网站",
        "url": "https://x-gpt.bwequation.com/",
        "update_frequency": 3600  # 秒
    }
]

# 数据库配置
DATABASE_URI = "sqlite:///bot_data.db"

# AI配置
AI_MODEL = "deepseek-chat"  # 使用DeepSeek模型名称
AI_TEMPERATURE = 0.7
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"  # 添加DeepSeek API URL 