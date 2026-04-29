# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 新增销售相关字段
运行方式: python migrate_add_sales_fields.py
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text

def migrate():
    """执行迁移"""
    app = create_app()
    
    with app.app_context():
        print("开始数据库迁移...")
        
        # 检测数据库类型
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        is_postgres = 'postgresql' in db_url.lower()
        print(f"数据库类型: {'PostgreSQL' if is_postgres else 'SQLite'}")
        
        # 获取连接
        connection = db.engine.connect()
        
        try:
            # ========== 1. Order表新增字段 ==========
            order_columns = [
                ('contact_person', 'VARCHAR(50)'),
                ('contact_phone', 'VARCHAR(20)'),
                ('total_amount', 'NUMERIC(12, 2) DEFAULT 0'),
                ('payment_status', 'VARCHAR(20) DEFAULT \'unpaid\''),
                ('paid_amount', 'NUMERIC(12, 2) DEFAULT 0'),
            ]
            
            for col_name, col_type in order_columns:
                try:
                    if is_postgres:
                        sql = text(f"SELECT column_name FROM information_schema.columns WHERE table_name='orders' AND column_name='{col_name}'")
                    else:
                        sql = text(f"PRAGMA table_info(orders)")
                    
                    result = connection.execute(sql)
                    
                    if is_postgres:
                        exists = result.fetchone() is not None
                    else:
                        exists = any(row[1] == col_name for row in result.fetchall())
                    
                    if not exists:
                        alter_sql = text(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type}")
                        connection.execute(alter_sql)
                        print(f"  ✓ Order表新增字段: {col_name}")
                    else:
                        print(f"  - Order表字段已存在: {col_name}")
                        
                except Exception as e:
                    print(f"  ! 处理字段 {col_name} 时出错: {e}")
            
            # ========== 2. Product表新增字段 ==========
            product_columns = [
                ('unit_price', 'NUMERIC(10, 2) DEFAULT 0'),
                ('amount', 'NUMERIC(10, 2) DEFAULT 0'),
                ('unit', 'VARCHAR(10) DEFAULT \'件\''),
            ]
            
            for col_name, col_type in product_columns:
                try:
                    if is_postgres:
                        sql = text(f"SELECT column_name FROM information_schema.columns WHERE table_name='products' AND column_name='{col_name}'")
                    else:
                        sql = text(f"PRAGMA table_info(products)")
                    
                    result = connection.execute(sql)
                    
                    if is_postgres:
                        exists = result.fetchone() is not None
                    else:
                        exists = any(row[1] == col_name for row in result.fetchall())
                    
                    if not exists:
                        alter_sql = text(f"ALTER TABLE products ADD COLUMN {col_name} {col_type}")
                        connection.execute(alter_sql)
                        print(f"  ✓ Product表新增字段: {col_name}")
                    else:
                        print(f"  - Product表字段已存在: {col_name}")
                        
                except Exception as e:
                    print(f"  ! 处理字段 {col_name} 时出错: {e}")
            
            # ========== 3. 创建Payment表 ==========
            try:
                if is_postgres:
                    sql = text("SELECT table_name FROM information_schema.tables WHERE table_name='payments'")
                else:
                    sql = text("SELECT name FROM sqlite_master WHERE type='table' AND name='payments'")
                
                result = connection.execute(sql)
                exists = result.fetchone() is not None
                
                if not exists:
                    create_payment_table = text("""
                        CREATE TABLE payments (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            order_id INTEGER NOT NULL,
                            amount NUMERIC(10, 2) NOT NULL,
                            payment_date DATETIME NOT NULL,
                            payment_method VARCHAR(20),
                            remark VARCHAR(200),
                            created_by INTEGER,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (order_id) REFERENCES orders (id),
                            FOREIGN KEY (created_by) REFERENCES users (id)
                        )
                    """)
                    
                    if is_postgres:
                        create_payment_table = text("""
                            CREATE TABLE payments (
                                id SERIAL PRIMARY KEY,
                                order_id INTEGER NOT NULL REFERENCES orders(id),
                                amount NUMERIC(10, 2) NOT NULL,
                                payment_date TIMESTAMP NOT NULL,
                                payment_method VARCHAR(20),
                                remark VARCHAR(200),
                                created_by INTEGER REFERENCES users(id),
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        """)
                    
                    connection.execute(create_payment_table)
                    print("  ✓ 创建Payment表")
                else:
                    print("  - Payment表已存在")
                    
            except Exception as e:
                print(f"  ! 创建Payment表时出错: {e}")
            
            # 提交事务
            connection.commit()
            print("\n✅ 迁移完成！")
            
        except Exception as e:
            connection.rollback()
            print(f"\n❌ 迁移失败: {e}")
            raise
        finally:
            connection.close()


def rollback():
    """回滚迁移（仅SQLite支持简单回滚）"""
    app = create_app()
    
    with app.app_context():
        print("警告：回滚操作会删除新增字段和Payment表！")
        confirm = input("确认继续？(yes/no): ")
        
        if confirm.lower() != 'yes':
            print("已取消")
            return
        
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        
        if 'postgresql' in db_url.lower():
            print("PostgreSQL 不支持自动回滚，请手动删除新增字段")
            return
        
        # SQLite 需要重建表来回滚
        print("SQLite 需要手动处理，建议重新初始化数据库")
        print("或手动执行 SQL 删除新增列")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        rollback()
    else:
        migrate()
