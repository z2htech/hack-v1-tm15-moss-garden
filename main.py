import logging
from config.config import *
from config.logging_config import setup_logging
from scraper.scraper import WebScraper
from ai_processor.processor import AIProcessor
from telegram_bot.bot import TelegramBot
from database.db_manager import DatabaseManager

def main():
    # 设置日志
    setup_logging()
    logger = logging.getLogger("main")
    logger.info("启动应用")
    
    # 初始化组件
    try:
        # 创建数据库管理器
        db_manager = DatabaseManager(DATABASE_URI)
        
        # 创建爬虫
        scraper = WebScraper(config={
            "TELEGRAM_API_TOKEN": TELEGRAM_API_TOKEN,
            "DEEPSEEK_API_KEY": DEEPSEEK_API_KEY,
            "AI_MODEL": AI_MODEL,
            "AI_TEMPERATURE": AI_TEMPERATURE,
            "DEEPSEEK_API_URL": DEEPSEEK_API_URL
        })
        
        # 创建AI处理器
        ai_processor = AIProcessor(config={
            "DEEPSEEK_API_KEY": DEEPSEEK_API_KEY,
            "DEEPSEEK_API_URL": DEEPSEEK_API_URL,
            "AI_MODEL": AI_MODEL,
            "AI_TEMPERATURE": AI_TEMPERATURE
        })
        
        # 创建并运行Telegram机器人
        bot = TelegramBot(
            config={
                "TELEGRAM_API_TOKEN": TELEGRAM_API_TOKEN,
                "DEEPSEEK_API_KEY": DEEPSEEK_API_KEY,
                "AI_MODEL": AI_MODEL,
                "AI_TEMPERATURE": AI_TEMPERATURE,
                "DEEPSEEK_API_URL": DEEPSEEK_API_URL,
                "WEBSITES": WEBSITES
            },
            ai_processor=ai_processor,
            scraper=scraper,
            db_manager=db_manager
        )
        
        # 运行机器人
        bot.run()
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}")

if __name__ == "__main__":
    main() 