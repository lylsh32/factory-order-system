"""
数据库迁移脚本：添加 order_no 和 customer_name 字段

使用方法：
1. 停止应用
2. 备份数据库文件（instance/factory.db）
3. 运行此脚本：python migrate_add_order_fields.py
4. 重启应用
"""

import sqlite3
import os
from datetime import datetime

def migrate():
    db_path = 'instance/factory.db'
    
    if not os.path.exists(db_path):
        print("数据库文件不存在，跳过迁移")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(orders)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'order_no' not in columns:
            print("添加 order_no 字段...")
            cursor.execute("ALTER TABLE orders ADD COLUMN order_no VARCHAR(50)")
        
        if 'customer_name' not in columns:
            print("添加 customer_name 字段...")
            cursor.execute("ALTER TABLE orders ADD COLUMN customer_name VARCHAR(100)")
        
        # 为现有订单生成订单号和客户名称
        cursor.execute("SELECT id, created_at FROM orders WHERE order_no IS NULL OR order_no = ''")
        orders = cursor.fetchall()
        
        for order_id, created_at in orders:
            # 生成订单号
            if created_at:
                try:
                    dt = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S.%f')
                except:
                    dt = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                date_str = dt.strftime('%Y%m%d')
            else:
                date_str = datetime.now().strftime('%Y%m%d')
            
            order_no = f"ORD-{date_str}-{str(order_id).zfill(3)}"
            
            # 更新订单
            cursor.execute(
                "UPDATE orders SET order_no = ?, customer_name = ? WHERE id = ?",
                (order_no, '历史客户', order_id)
            )
        
        conn.commit()
        print(f"迁移完成！处理了 {len(orders)} 条订单")
        
    except Exception as e:
        print(f"迁移失败：{e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
