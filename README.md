# 🏭 工厂排单系统

一个基于 Flask 的工厂订单生产管理系统，支持多角色管理、订单状态流转、CAD图纸上传下载等功能。

## 📋 功能特性

### 三种用户角色
- **管理员 (admin)**: 全部权限 + 用户管理 + 订单分配
- **跟单员 (sales)**: 下单、查看订单、上传图纸、暂停/取消订单
- **生产人员 (worker)**: 查看待产订单、下载图纸、标记完成

### 订单状态流转
```
待生产 → 进行中 → 已完成
   ↓        ↓
 已取消   已暂停
```

### 核心功能
- ✅ 用户权限管理（添加、禁用、删除）
- ✅ 订单创建与管理
- ✅ 订单状态实时更新
- ✅ CAD图纸上传（支持 .dwg/.dxf/.pdf）
- ✅ 图纸下载功能
- ✅ 订单分配给生产人员
- ✅ 响应式设计（支持手机/平板/电脑）
- ✅ 现代化美观的 UI 界面

## 🛠 技术栈

- **后端**: Python 3.x + Flask
- **数据库**: SQLite（内置，无需额外安装）
- **前端**: Bootstrap 5 + jQuery
- **文件存储**: 本地文件系统

## 🚀 快速开始

### 环境要求
- Python 3.8 或更高版本
- pip 包管理器

### 安装步骤

#### 1. 克隆或下载项目
```bash
cd 工厂排单系统
```

#### 2. 创建虚拟环境（推荐）
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

#### 3. 安装依赖
```bash
pip install -r requirements.txt
```

#### 4. 运行应用
```bash
python app.py
```

#### 5. 访问系统
打开浏览器访问: **http://127.0.0.1:5000**

## 🔐 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |

> ⚠️ **重要**: 首次登录后请立即修改默认密码！

## ☁️ 云服务器部署指南

### 使用 Gunicorn + Nginx（生产环境推荐）

#### 1. 安装服务器依赖
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3-venv nginx

# CentOS
sudo yum install python3 nginx
```

#### 2. 创建系统用户
```bash
sudo useradd -m -s /bin/bash factory
sudo mkdir -p /var/www/factory
sudo chown factory:factory /var/www/factory
```

#### 3. 部署应用
```bash
# 切换到部署用户
sudo su - factory

# 上传项目文件到 /var/www/factory
cd /var/www/factory

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install gunicorn

# 创建必要的目录
mkdir -p uploads instance

# 测试运行
python app.py
```

#### 4. 配置 Gunicorn
创建 systemd 服务文件 `/etc/systemd/system/factory.service`:
```ini
[Unit]
Description=Factory Order System
After=network.target

[Service]
User=factory
Group=factory
WorkingDirectory=/var/www/factory
Environment="PATH=/var/www/factory/venv/bin"
ExecStart=/var/www/factory/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target
```

启动服务:
```bash
sudo systemctl daemon-reload
sudo systemctl enable factory
sudo systemctl start factory
```

#### 5. 配置 Nginx 反向代理
创建配置文件 `/etc/nginx/sites-available/factory`:
```nginx
server {
    listen 80;
    server_name your_domain.com;  # 替换为你的域名或IP

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /uploads {
        alias /var/www/factory/uploads;
    }
}
```

启用站点:
```bash
sudo ln -s /etc/nginx/sites-available/factory /etc/nginx/sites-enabled/
sudo nginx -t  # 测试配置
sudo systemctl reload nginx
```

#### 6. 配置防火墙
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp  # 如果使用HTTPS
```

#### 7. 配置 HTTPS（可选但强烈推荐）
使用 Let's Encrypt 免费证书:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your_domain.com
```

### 使用 Docker 部署（可选）

创建 `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN mkdir -p uploads instance

EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

构建和运行:
```bash
docker build -t factory-order .
docker run -d -p 5000:5000 -v $(pwd)/uploads:/app/uploads -v $(pwd)/instance:/app/instance factory-order
```

## 📁 项目结构

```
工厂排单系统/
├── app.py              # 主应用入口
├── models.py           # 数据库模型
├── auth.py             # 认证模块
├── config.py           # 配置文件
├── requirements.txt    # Python依赖
├── routes/             # 路由模块
│   ├── __init__.py
│   ├── order.py        # 订单管理
│   └── admin.py        # 管理员功能
├── templates/          # HTML模板
│   ├── base.html       # 基础模板
│   ├── login.html      # 登录页
│   ├── dashboard.html # 控制台
│   ├── create_order.html
│   ├── order_list.html
│   ├── order_detail.html
│   ├── admin.html
│   ├── user_list.html
│   ├── admin_orders.html
│   ├── 404.html
│   └── 500.html
├── uploads/            # 图纸存储目录
├── instance/          # SQLite数据库
└── README.md          # 部署文档
```

## ⚙️ 配置说明

### 配置文件 (config.py)

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| SECRET_KEY | 动态生成 | Flask密钥 |
| SQLALCHEMY_DATABASE_URI | sqlite:///instance/factory.db | 数据库路径 |
| UPLOAD_FOLDER | uploads | 上传文件存储目录 |
| MAX_CONTENT_LENGTH | 20MB | 单文件最大大小 |
| ALLOWED_EXTENSIONS | {dwg, dxf, pdf} | 允许的文件类型 |
| DEFAULT_ADMIN_USERNAME | admin | 默认管理员用户名 |
| DEFAULT_ADMIN_PASSWORD | admin123 | 默认管理员密码 |

### 修改密码
首次部署后，请修改 `config.py` 中的 `SECRET_KEY` 和默认管理员密码。

## 🔧 常见问题

### Q: 上传文件失败？
1. 检查 `uploads/` 目录是否存在且有写入权限
2. 检查文件大小是否超过 20MB 限制
3. 检查文件格式是否为 .dwg/.dxf/.pdf

### Q: 数据库报错？
确保 `instance/` 目录存在且有写入权限。

### Q: 无法访问？
1. 检查防火墙是否开放 5000 端口
2. 检查 Gunicorn/Nginx 服务状态
3. 查看日志: `sudo journalctl -u factory -f`

## 📝 开发说明

### 添加新用户（命令行）
```bash
python -c "
from app import app
from models import db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    # 添加用户
    user = User(
        username='newuser',
        password=generate_password_hash('password123'),
        name='新用户',
        role='worker',
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    print('用户创建成功')
"
```

### 备份数据库
```bash
cp instance/factory.db instance/factory.db.backup
```

## 📄 许可证

MIT License

## 🤝 技术支持

如有问题，请联系系统管理员。
