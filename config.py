import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'factory-order-system-secret-key-2024'
    
    # 数据库配置：优先使用环境变量（云平台），否则使用本地 SQLite
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Railway/Heroku 的 PostgreSQL URL 格式转换
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'factory.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 上传文件夹配置
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20MB max file size
    ALLOWED_EXTENSIONS = {'dwg', 'dxf', 'pdf'}
    
    # Default admin credentials
    DEFAULT_ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    DEFAULT_ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'
