# Moss_bot - 基于顶级交易员推文分析的投资机器人

## 项目介绍

Moss_bot是一个专为加密货币交易爱好者开发的机器人，旨在实时监控顶级交易员的Twitter动态并进行情绪分析，帮助用户快速获取市场情绪和趋势信息。系统通过自动爬取、分析交易员推文，并将有价值的市场洞察通过Telegram机器人推送给用户。

## 主要功能

- **实时监控**：自动爬取顶级交易员最近的Twitter动态
- **情绪分析**：分析每条推文对应的情绪标签(positive/neutral/negative)、分析原因和详细解释
- **资产关联**：识别推文中提及的加密货币资产
- **Telegram推送**：通过Telegram机器人实时接收市场洞察，综合最近24小时的推文，判断市场走向

## 技术架构

项目由以下几个核心模块组成：

1. **爬虫模块(scraper)**：使用Selenium和BeautifulSoup爬取交易员推文信息
2. **AI处理模块(ai_processor)**：处理和分析爬取的数据
3. **数据库模块(database)**：存储交易员信息和历史数据
4. **Telegram机器人(telegram_bot)**：用户交互界面
5. **配置模块(config)**：系统配置和参数管理

## Quick Start

### 环境要求
- Python 3.8+
- Chrome浏览器 (用于Selenium爬虫)

### 安装过程

1. 克隆仓库
   ```
   git clone https://github.com/z2htech/hack-v1-tm15-moss-garden
   cd moss-garden
   ```

2. 创建并激活虚拟环境
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # 或
   .venv\Scripts\activate  # Windows
   ```

3. 安装依赖
   ```
   pip install -r requirements.txt
   ```

4. 配置参数
   - 在`config`目录中创建或修改配置文件
   - 设置Telegram Bot API Token
   - 设置DeepSeek API密钥（或者使用其他模型）

## 使用方法

1. 启动系统
   ```
   python main.py
   ```

2. 通过Telegram与机器人交互
   - 开始使用: `/start`
   - 显示机器人的功能: `/help`
   - 获取顶级交易员最近24小时的市场观点: `/summary`
   - 与AI助手对话，询问有关交易员推文的信息: `/ai`

## 开发说明

- `scraper/scraper.py`: 爬虫核心代码，负责爬取交易员推文和情绪数据
- `telegram_bot/bot.py`: Telegram机器人实现
- `database/db_manager.py`: 数据库管理
- `ai_processor/processor.py`: AI分析处理器
- `main.py`: 应用入口点

## 项目特色

本项目不同于一般的Twitter爬虫，它特别关注加密货币交易领域的顶级交易员，并且直接从网页中提取情绪数据，包括情绪标签、原因和详细解释，为用户提供更准确的市场洞察。

## 贡献者

- [Lambert Lin](https://github.com/lambertalpha)
- [Shiyu Chen](https://github.com/csy143)

## 许可证

MIT