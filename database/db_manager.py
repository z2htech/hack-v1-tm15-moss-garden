import sqlite3
import json
import logging
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_uri):
        self.db_uri = db_uri
        self.logger = logging.getLogger("database")
        
        # 从URI中提取SQLite文件路径
        if db_uri.startswith("sqlite:///"):
            self.db_file = db_uri[10:]
        else:
            self.db_file = db_uri
            
        # 初始化数据库
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # 创建数据表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                url TEXT NOT NULL,
                summary TEXT NOT NULL,
                original_data TEXT NOT NULL,
                processed_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            ''')
            
            conn.commit()
            conn.close()
            self.logger.info("数据库初始化成功")
        except Exception as e:
            self.logger.error(f"数据库初始化失败: {str(e)}")
    
    def save_processed_data(self, processed_data):
        """保存处理后的数据到数据库"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            source = processed_data["original_data"]["source"]
            url = processed_data["original_data"]["url"]
            summary = processed_data["summary"]
            original_data = json.dumps(processed_data["original_data"], ensure_ascii=False)
            processed_at = processed_data["processed_at"]
            created_at = datetime.now().isoformat()
            
            cursor.execute('''
            INSERT INTO processed_data 
            (source, url, summary, original_data, processed_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (source, url, summary, original_data, processed_at, created_at))
            
            conn.commit()
            conn.close()
            self.logger.info(f"保存数据成功: {source}")
            return True
        except Exception as e:
            self.logger.error(f"保存数据失败: {str(e)}")
            return False
    
    def get_latest_data(self, limit=5):
        """获取最新的处理数据"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, source, url, summary, processed_at 
            FROM processed_data 
            ORDER BY created_at DESC 
            LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            conn.close()
            
            data = []
            for row in results:
                data.append({
                    "id": row[0],
                    "source": row[1],
                    "url": row[2],
                    "summary": row[3],
                    "processed_at": row[4]
                })
            
            return data
        except Exception as e:
            self.logger.error(f"获取数据失败: {str(e)}")
            return []
    
    def get_data_by_source(self, source, limit=10):
        """按来源获取处理数据"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, source, url, summary, processed_at 
            FROM processed_data 
            WHERE source = ?
            ORDER BY created_at DESC 
            LIMIT ?
            ''', (source, limit))
            
            results = cursor.fetchall()
            conn.close()
            
            data = []
            for row in results:
                data.append({
                    "id": row[0],
                    "source": row[1],
                    "url": row[2],
                    "summary": row[3],
                    "processed_at": row[4]
                })
            
            return data
        except Exception as e:
            self.logger.error(f"获取数据失败: {str(e)}")
            return [] 