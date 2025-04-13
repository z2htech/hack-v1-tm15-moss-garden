from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging
import json
import re

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
        self.app.add_handler(CommandHandler("ai", self.ai_command))
        
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
        /ai - 与AI助手对话，询问有关交易员推文的信息
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
                    f"顶级交易员市场观点汇总:\n\n{result['summary']}",
                    parse_mode="Markdown"
                )
        else:
            await update.message.reply_text("抱歉，没有获取到新信息。")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # 处理用户发送的消息
        user_message = update.message.text
        await update.message.reply_text(f"收到你的消息: {user_message}\n使用 /help 查看可用命令。")
    
    async def ai_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理与AI的对话"""
        message_text = update.message.text
        
        # 提取用户指令 (/ai 之后的文本)
        user_query = message_text.replace("/ai", "", 1).strip()
        
        if not user_query:
            # 如果用户只发送了/ai命令，没有附带问题
            await update.message.reply_text(
                "请在/ai命令后输入您的问题，例如：\n"
                "/ai 有哪些交易员看好比特币?\n"
                "/ai 最近市场的主要风险是什么?\n"
                "/ai 分析一下Andrew Kang的观点"
            )
            return
        
        await update.message.reply_text("正在分析交易员数据以回答您的问题，请稍候...")
        
        try:
            # 读取最新的推文数据
            try:
                with open("extracted_tweets.json", "r", encoding="utf-8") as f:
                    tweets_data = json.load(f)
            except Exception as e:
                self.logger.error(f"读取推文数据失败: {str(e)}")
                await update.message.reply_text("抱歉，无法读取最新的交易员数据。")
                return
            
            # 调用AI处理器来回答用户问题
            answer = await self.ai_processor.answer_question(user_query, tweets_data)
            
            if answer:
                # 调整格式使其符合Telegram Markdown格式
                # 1. 将Markdown的### 标题格式替换为*加粗文字*
                answer = re.sub(r'### (.*)', r'*\1*', answer)
                # 2. 确保引用块前后有空行并使用>符号
                answer = re.sub(r'> (.*)', r'\n> \1\n', answer)
                # 3. 用一行连字符替换多行连字符作为分隔线
                answer = re.sub(r'---+', r'------', answer)
                
                # 发送消息时启用Markdown解析
                await update.message.reply_text(answer, parse_mode="Markdown")
            else:
                await update.message.reply_text("抱歉，AI处理您的问题时遇到了困难。请稍后再试或尝试重新表述您的问题。")
        
        except Exception as e:
            self.logger.error(f"AI对话处理失败: {str(e)}")
            await update.message.reply_text("处理您的请求时发生错误，请稍后再试。")
    
    async def error_handler(self, update, context):
        self.logger.error(f"更新 {update} 导致错误 {context.error}")
        
    def run(self):
        self.logger.info("启动Telegram机器人")
        self.app.run_polling() 