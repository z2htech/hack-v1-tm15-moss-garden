from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging

class TelegramBot:
    def __init__(self, config, ai_processor, scraper, db_manager):
        self.config = config
        self.ai_processor = ai_processor
        self.scraper = scraper
        self.db_manager = db_manager
        self.logger = logging.getLogger("telegram_bot")
        
        # 创建机器人应用
        self.app = Application.builder().token(config["TELEGRAM_API_TOKEN"]).build()
        
        # 注册处理器
        self._register_handlers()
    
    def _register_handlers(self):
        # 命令处理器
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("summary", self.new_command))
        
        # 消息处理器
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # 错误处理
        self.app.add_error_handler(self.error_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("欢迎使用信息爬取机器人！使用 /help 查看可用命令。")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
        可用命令:
        /start - 开始使用机器人
        /help - 显示机器人的功能
        /summary - 获取顶级交易员最近24小时的市场观点
        """
        await update.message.reply_text(help_text)
    
    async def new_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("正在获取交易员最近24小时的推文并总结其市场观点，请稍候...")
        
        # 爬取数据
        results = []
        for website in self.config["WEBSITES"]:
            scraped_data = self.scraper.scrape_website(website)
            if scraped_data:
                # 处理数据
                processed_data = await self.ai_processor.process_data(scraped_data)
                if processed_data:
                    results.append(processed_data)
                    # 保存到数据库
                    self.db_manager.save_processed_data(processed_data)
        
        if results:
            for result in results:
                await update.message.reply_text(
                    f"顶级交易员市场观点汇总:\n\n"
                    f"{result['summary']}\n\n"
                    f"数据来源: {result['original_data']['url']}"
                )
        else:
            await update.message.reply_text("抱歉，没有获取到新信息。")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # 处理用户发送的消息
        user_message = update.message.text
        await update.message.reply_text(f"收到你的消息: {user_message}\n使用 /help 查看可用命令。")
    
    async def error_handler(self, update, context):
        self.logger.error(f"更新 {update} 导致错误 {context.error}")
        
    def run(self):
        self.logger.info("启动Telegram机器人")
        self.app.run_polling() 