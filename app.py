import os
from flask import Flask, flash, redirect, url_for
from flask_login import current_user
from config import Config
from models import db, User
from auth import auth_bp, init_login_manager
from routes.order import order_bp
from routes.admin import admin_bp
from werkzeug.security import generate_password_hash

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 确保必要的目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('instance', exist_ok=True)
    
    # 初始化扩展
    db.init_app(app)
    login_manager = init_login_manager(app)
    
    # 注册蓝图
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
