from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from decimal import Decimal

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
    payments = db.relationship('Payment', backref='creator', lazy=True)
    
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
    order_no = db.Column(db.String(50), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    
    # 新增联系人字段
    contact_person = db.Column(db.String(50), nullable=True)  # 联系人
    contact_phone = db.Column(db.String(20), nullable=True)   # 联系电话
    
    remark = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='quoting')  # quoting/confirmed/pending/producing/completed/cancelled/paused
    
    # 新增金额字段
    total_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'))  # 订单总金额
    payment_status = db.Column(db.String(20), default='unpaid')  # unpaid/partial/paid
    paid_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'))  # 已付金额
    
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    products = db.relationship('Product', backref='order', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Order {self.order_no}>'
    
    @property
    def total_quantity(self):
        """计算订单总数量"""
        return sum(p.quantity for p in self.products)
    
    def get_status_text(self):
        status_map = {
            'quoting': '报价中',
            'confirmed': '已确认',
            'pending': '待生产',
            'producing': '进行中',
            'completed': '已完成',
            'cancelled': '已取消',
            'paused': '已暂停'
        }
        return status_map.get(self.status, self.status)
    
    def get_payment_status_text(self):
        """获取付款状态中文"""
        status_map = {
            'unpaid': '未付款',
            'partial': '部分付款',
            'paid': '已付清'
        }
        return status_map.get(self.payment_status, self.payment_status)
    
    def update_payment_status(self):
        """更新付款状态"""
        if self.paid_amount and self.total_amount:
            if Decimal(str(self.paid_amount)) >= Decimal(str(self.total_amount)):
                self.payment_status = 'paid'
            elif Decimal(str(self.paid_amount)) > 0:
                self.payment_status = 'partial'
            else:
                self.payment_status = 'unpaid'
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_no': self.order_no,
            'customer_name': self.customer_name,
            'contact_person': self.contact_person,
            'contact_phone': self.contact_phone,
            'remark': self.remark,
            'status': self.status,
            'status_text': self.get_status_text(),
            'total_amount': float(self.total_amount) if self.total_amount else 0,
            'payment_status': self.payment_status,
            'payment_status_text': self.get_payment_status_text(),
            'paid_amount': float(self.paid_amount) if self.paid_amount else 0,
            'created_by': self.created_by,
            'created_by_name': self.creator.name if self.creator else '',
            'assigned_to': self.assigned_to,
            'assigned_to_name': self.assignee.name if self.assignee else '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M'),
            'products': [p.to_dict() for p in self.products],
            'total_quantity': self.total_quantity
        }

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    length = db.Column(db.Float, nullable=False)
    width = db.Column(db.Float, nullable=False)
    thickness = db.Column(db.Float, nullable=True)
    color = db.Column(db.String(50), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    screenshot = db.Column(db.Text, nullable=True)
    
    # 新增销售字段
    unit_price = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))  # 单价
    amount = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))       # 金额
    unit = db.Column(db.String(10), default='件')                        # 单位
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    attachments = db.relationship('Attachment', backref='product', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Product {self.product_name}>'
    
    def calculate_amount(self):
        """计算金额"""
        if self.quantity and self.unit_price:
            return Decimal(str(self.quantity)) * Decimal(str(self.unit_price))
        return Decimal('0.00')
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_name': self.product_name,
            'length': self.length,
            'width': self.width,
            'thickness': self.thickness,
            'color': self.color,
            'quantity': self.quantity,
            'screenshot': self.screenshot,
            'unit_price': float(self.unit_price) if self.unit_price else 0,
            'amount': float(self.amount) if self.amount else 0,
            'unit': self.unit,
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

class Payment(db.Model):
    """付款记录表（新增）"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False)
    payment_method = db.Column(db.String(20), nullable=True)  # cash/transfer/wechat/alipay
    remark = db.Column(db.String(200), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_payment_method_text(self):
        """获取付款方式中文"""
        method_map = {
            'cash': '现金',
            'transfer': '转账',
            'wechat': '微信',
            'alipay': '支付宝'
        }
        return method_map.get(self.payment_method, self.payment_method or '未指定')
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'amount': float(self.amount),
            'payment_date': self.payment_date.strftime('%Y-%m-%d %H:%M'),
            'payment_method': self.payment_method,
            'payment_method_text': self.get_payment_method_text(),
            'remark': self.remark,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }
