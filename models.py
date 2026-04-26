from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, sales, worker
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    created_orders = db.relationship('Order', foreign_keys='Order.created_by', backref='creator', lazy=True)
    assigned_orders = db.relationship('Order', foreign_keys='Order.assigned_to', backref='assignee', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'name': self.name,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(50), unique=True, nullable=False)  # 订单号，格式：ORD-YYYYMMDD-XXX
    customer_name = db.Column(db.String(100), nullable=False)  # 客户名称
    remark = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, producing, completed, cancelled, paused
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    products = db.relationship('Product', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Order {self.order_no}>'
    
    @property
    def total_quantity(self):
        """计算订单总数量"""
        return sum(p.quantity for p in self.products)
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'customer_name': self.customer_name,
            'remark': self.remark,
            'status': self.status,
            'status_text': self.get_status_text(),
            'created_by': self.created_by,
            'created_by_name': self.creator.name if self.creator else '',
            'assigned_to': self.assigned_to,
            'assigned_to_name': self.assignee.name if self.assignee else '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M'),
            'products': [p.to_dict() for p in self.products],
            'total_quantity': self.total_quantity
        }
    
    def get_status_text(self):
        status_map = {
            'pending': '待生产',
            'producing': '进行中',
            'completed': '已完成',
            'cancelled': '已取消',
            'paused': '已暂停'
        }
        return status_map.get(self.status, self.status)

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    length = db.Column(db.Float, nullable=False)
    width = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    attachments = db.relationship('Attachment', backref='product', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Product {self.product_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_name': self.product_name,
            'length': self.length,
            'width': self.width,
            'quantity': self.quantity,
            'attachments': [a.to_dict() for a in self.attachments]
        }

class Attachment(db.Model):
    __tablename__ = 'attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Attachment {self.filename}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'filepath': self.filepath,
            'uploaded_at': self.uploaded_at.strftime('%Y-%m-%d %H:%M')
        }
