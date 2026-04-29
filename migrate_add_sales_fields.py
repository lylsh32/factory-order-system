# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 添加销售功能相关字段
适用于已有数据库的迁移，兼容已有数据
"""

import sys
import os
from decimal import Decimal
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db
from flask import Flask


def create_app():
    """创建Flask应用实例"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 
        'sqlite:///factory_orders.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app


def migrate_add_sales_fields():
    """
    执行迁移：添加销售功能相关字段
    
    Product表新增：
    - unit_price (Decimal(10,2)) - 单价
    - amount (Decimal(10,2)) - 金额
    - unit (String(10)) - 单位
    
    Order表新增：
    - contact_person (String(50)) - 联系人
    - contact_phone (String(20)) - 联系电话
    - total_amount (Decimal(12,2)) - 订单总金额
    - payment_status (String(20)) - 付款状态
    - paid_amount (Decimal(12,2)) - 已付金额
    
    新建Payment表
    """
    app = create_app()
    
    with app.app_context():
        # 获取数据库连接
        connection = db.engine.connect()
        
        try:
            # 检查并添加 product 表字段
            migrate_product_table(connection)
            
            # 检查并添加 order 表字段
            migrate_order_table(connection)
            
            # 创建 payment 表
            create_payment_table(connection)
            
            print("\n✅ 迁移完成！")
            print("\n新增/变更内容：")
            print("  - Product表: unit_price, amount, unit")
            print("  - Order表: contact_person, contact_phone, total_amount, payment_status, paid_amount")
            print("  - Payment表: 新建（付款记录）")
            
        except Exception as e:
            print(f"\n❌ 迁移失败: {e}")
            connection.rollback()
            raise
        finally:
            connection.close()


def column_exists(connection, table_name, column_name):
    """检查列是否存在"""
    if 'sqlite' in str(db.engine):
        # SQLite检查方式
        result = connection.execute(
            f"PRAGMA table_info({table_name})"
        )
        columns = [row[1] for row in result]
        return column_name in columns
    else:
        # PostgreSQL检查方式
        result = connection.execute(
            f"""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = '{table_name}' AND column_name = '{column_name}'
            """
        )
        return result.fetchone() is not None


def table_exists(connection, table_name):
    """检查表是否存在"""
    if 'sqlite' in str(db.engine):
        result = connection.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
        )
    else:
        result = connection.execute(
            f"SELECT table_name FROM information_schema.tables WHERE table_name = '{table_name}'"
        )
    return result.fetchone() is not None


def migrate_product_table(connection):
    """迁移Product表"""
    print("\n📦 迁移 Product 表...")
    
    # unit_price 字段
    if not column_exists(connection, 'product', 'unit_price'):
        connection.execute(
            "ALTER TABLE product ADD COLUMN unit_price NUMERIC(10, 2) DEFAULT 0.00"
        )
        print("  ✓ 添加 unit_price 字段")
    else:
        print("  - unit_price 字段已存在")
    
    # amount 字段
    if not column_exists(connection, 'product', 'amount'):
        connection.execute(
            "ALTER TABLE product ADD COLUMN amount NUMERIC(10, 2) DEFAULT 0.00"
        )
        print("  ✓ 添加 amount 字段")
    else:
        print("  - amount 字段已存在")
    
    # unit 字段
    if not column_exists(connection, 'product', 'unit'):
        connection.execute(
            "ALTER TABLE product ADD COLUMN unit VARCHAR(10) DEFAULT '件'"
        )
        print("  ✓ 添加 unit 字段")
    else:
        print("  - unit 字段已存在")
    
    connection.commit()


def migrate_order_table(connection):
    """迁移Order表"""
    print("\n📦 迁移 Order 表...")
    
    # contact_person 字段
    if not column_exists(connection, 'order', 'contact_person'):
        connection.execute(
            "ALTER TABLE order_table ADD COLUMN contact_person VARCHAR(50)"
        )
        print("  ✓ 添加 contact_person 字段")
    else:
        print("  - contact_person 字段已存在")
    
    # contact_phone 字段
    if not column_exists(connection, 'order', 'contact_phone'):
        connection.execute(
            "ALTER TABLE order_table ADD COLUMN contact_phone VARCHAR(20)"
        )
        print("  ✓ 添加 contact_phone 字段")
    else:
        print("  - contact_phone 字段已存在")
    
    # total_amount 字段
    if not column_exists(connection, 'order', 'total_amount'):
        connection.execute(
            "ALTER TABLE order_table ADD COLUMN total_amount NUMERIC(12, 2) DEFAULT 0.00"
        )
        print("  ✓ 添加 total_amount 字段")
    else:
        print("  - total_amount 字段已存在")
    
    # payment_status 字段
    if not column_exists(connection, 'order', 'payment_status'):
        connection.execute(
            "ALTER TABLE order_table ADD COLUMN payment_status VARCHAR(20) DEFAULT 'unpaid'"
        )
        print("  ✓ 添加 payment_status 字段")
    else:
        print("  - payment_status 字段已存在")
    
    # paid_amount 字段
    if not column_exists(connection, 'order', 'paid_amount'):
        connection.execute(
            "ALTER TABLE order_table ADD COLUMN paid_amount NUMERIC(12, 2) DEFAULT 0.00"
        )
        print("  ✓ 添加 paid_amount 字段")
    else:
        print("  - paid_amount 字段已存在")
    
    connection.commit()


def create_payment_table(connection):
    """创建Payment表"""
    print("\n💳 创建 Payment 表...")
    
    if table_exists(connection, 'payment'):
        print("  - payment 表已存在")
        return
    
    # 注意：SQLite不支持 IF NOT EXISTS，需要先检查
    if 'sqlite' in str(db.engine):
        create_sql = """
        CREATE TABLE IF NOT EXISTS payment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            amount NUMERIC(10, 2) NOT NULL,
            payment_date TIMESTAMP NOT NULL,
            payment_method VARCHAR(20),
            remark VARCHAR(200),
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES order_table (id),
            FOREIGN KEY (created_by) REFERENCES user (id)
        )
        """
    else:
        create_sql = """
        CREATE TABLE payment (
            id SERIAL PRIMARY KEY,
            order_id INTEGER NOT NULL,
            amount NUMERIC(10, 2) NOT NULL,
            payment_date TIMESTAMP NOT NULL,
            payment_method VARCHAR(20),
            remark VARCHAR(200),
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES order_table (id),
            FOREIGN KEY (created_by) REFERENCES user (id)
        )
        """
    
    connection.execute(create_sql)
    connection.commit()
    print("  ✓ payment 表创建成功")


def rollback_migration():
    """
    回滚迁移（如果需要）
    注意：这是可选操作，仅在需要撤销迁移时使用
    """
    app = create_app()
    
    with app.app_context():
        connection = db.engine.connect()
        
        try:
            print("\n⚠️  开始回滚迁移...")
            
            # 删除payment表
            if table_exists(connection, 'payment'):
                connection.execute("DROP TABLE IF EXISTS payment")
                print("  ✓ 删除 payment 表")
            
            # SQLite不支持删除列，所以只打印提示
            if 'sqlite' in str(db.engine):
                print("  ⚠️  SQLite不支持删除列，请手动清理")
            else:
                # PostgreSQL可以删除列
                connection.execute("ALTER TABLE order_table DROP COLUMN IF EXISTS paid_amount")
                connection.execute("ALTER TABLE order_table DROP COLUMN IF EXISTS payment_status")
                connection.execute("ALTER TABLE order_table DROP COLUMN IF EXISTS total_amount")
                connection.execute("ALTER TABLE order_table DROP COLUMN IF EXISTS contact_phone")
                connection.execute("ALTER TABLE order_table DROP COLUMN IF EXISTS contact_person")
                connection.execute("ALTER TABLE product DROP COLUMN IF EXISTS amount")
                connection.execute("ALTER TABLE product DROP COLUMN IF EXISTS unit_price")
                connection.execute("ALTER TABLE product DROP COLUMN IF EXISTS unit")
                print("  ✓ 删除 Order 和 Product 表的新增列")
            
            connection.commit()
            print("\n✅ 回滚完成！")
            
        except Exception as e:
            print(f"\n❌ 回滚失败: {e}")
            connection.rollback()
            raise
        finally:
            connection.close()


if __name__ == '__main__':
    print("=" * 50)
    print("工厂排单系统 - 销售功能迁移脚本")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        rollback_migration()
    else:
        migrate_add_sales_fields()
