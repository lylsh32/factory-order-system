import os
from flask import Flask, flash, redirect, url_for
from flask_login import current_user
from config import Config
from models import db, User
from auth import auth_bp, init_login_manager
from routes.order import order_bp
from routes.admin import admin_bp
from werkzeug.security import generate_password_hash
from sqlalchemy import text


def run_migrations(app):
    """自动运行数据库迁移"""
    with app.app_context():
        print("检查数据库迁移...")
        
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        is_postgres = 'postgresql' in db_url.lower()
        
        try:
            connection = db.engine.connect()
            
            # ========== Order表新增字段 ==========
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
                        sql = text("PRAGMA table_info(orders)")
                    
                    result = connection.execute(sql)
                    
                    if is_postgres:
                        exists = result.fetchone() is not None
                    else:
                        exists = any(row[1] == col_name for row in result.fetchall())
                    
                    if not exists:
                        alter_sql = text(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type}")
                        connection.execute(alter_sql)
                        connection.commit()
                        print(f"  ✓ Order表新增字段: {col_name}")
                    else:
                        print(f"  - Order表字段已存在: {col_name}")
                        
                except Exception as e:
                    print(f"  ! 字段 {col_name}: {e}")
            
            # ========== Product表新增字段 ==========
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
                        sql = text("PRAGMA table_info(products)")
                    
                    result = connection.execute(sql)
                    
                    if is_postgres:
                        exists = result.fetchone() is not None
                    else:
                        exists = any(row[1] == col_name for row in result.fetchall())
                    
                    if not exists:
                        alter_sql = text(f"ALTER TABLE products ADD COLUMN {col_name} {col_type}")
                        connection.execute(alter_sql)
                        connection.commit()
                        print(f"  ✓ Product表新增字段: {col_name}")
                    else:
                        print(f"  - Product表字段已存在: {col_name}")
                        
                except Exception as e:
                    print(f"  ! 字段 {col_name}: {e}")
            
            # ========== 创建Payment表 ==========
            try:
                if is_postgres:
                    sql = text("SELECT table_name FROM information_schema.tables WHERE table_name='payments'")
                else:
                    sql = text("SELECT name FROM sqlite_master WHERE type='table' AND name='payments'")
                
                result = connection.execute(sql)
                exists = result.fetchone() is not None
                
                if not exists:
                    if is_postgres:
                        create_sql = text("""
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
                    else:
                        create_sql = text("""
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
                    
                    connection.execute(create_sql)
                    connection.commit()
                    print("  ✓ 创建Payment表")
                else:
                    print("  - Payment表已存在")
                    
            except Exception as e:
                print(f"  ! Payment表: {e}")
            
            connection.close()
            print("迁移检查完成\n")
            
        except Exception as e:
            print(f"迁移检查跳过: {e}\n")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 确保必要的目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('instance', exist_ok=True)
    
    # 初始化扩展
    db.init_app(app)
    login_manager = init_login_manager(app)
    
    # 运行数据库迁移（在create_all之前）
    run_migrations(app)
    
    # 注册蓝图 - 注意顺序：admin 带前缀，必须先注册
    app.register_blueprint(admin_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(auth_bp)
    
    # 创建数据库和默认管理员
    with app.app_context():
        db.create_all()
        
        # 检查并创建默认管理员
        admin_username = app.config.get('DEFAULT_ADMIN_USERNAME', 'admin')
        admin_password = app.config.get('DEFAULT_ADMIN_PASSWORD', 'admin123')
        
        if not User.query.filter_by(username=admin_username).first():
            admin = User(
                username=admin_username,
                password=generate_password_hash(admin_password),
                name='系统管理员',
                role='admin',
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            print(f'✓ 默认管理员账号已创建: {admin_username} / {admin_password}')
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        return render_template('500.html'), 500
    
    # 模板上下文处理器
    @app.context_processor
    def inject_user():
        return dict(current_user=current_user)
    
    return app

app = create_app()

if __name__ == '__main__':
    print('\n' + '='*50)
    print('🏭 工厂排单系统启动中...')
    print('='*50)
    print('📍 访问地址: http://127.0.0.1:5000')
    print('👤 默认管理员: admin / admin123')
    print('='*50 + '\n')
    
    app.run(host='0.0.0.0', port=5000, debug=True)
