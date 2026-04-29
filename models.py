# -*- coding: utf-8 -*-
"""
工厂排单系统 - 数据模型
包含 Product、Order、Payment 等模型
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from decimal import Decimal

db = SQLAlchemy()


class User(db.Model):
    """用户模型"""
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin/admin_assistant/clerks/production
    full_name = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联
    orders_created = db.relationship('Order', backref='creator', lazy='dynamic')
    payments = db.relationship('Payment', backref='creator', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'


class Product(db.Model):
    """产品模型（订单明细）"""
    __tablename__ = 'product'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    
    # 产品信息
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit = db.Column(db.String(10), default='件')  # 单位
    
    # 销售相关字段（新增）
    unit_price = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))  # 单价
    amount = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))  # 金额 = 数量 × 单价
    
    # 产品规格
    color = db.Column(db.String(20))  # 颜色
    size = db.Column(db.String(50))  # 尺寸
    weight = db.Column(db.String(30))  # 克重
    material = db.Column(db.String(50))  # 材质
    craft = db.Column(db.String(100))  # 工艺要求
    other_requirements = db.Column(db.Text)  # 其他要求
    remark = db.Column(db.String(200))  # 备注

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def calculate_amount(self):
        """计算金额：数量 × 单价"""
        if self.quantity and self.unit_price:
            return Decimal(str(self.quantity)) * Decimal(str(self.unit_price))
        return Decimal('0.00')

    def __repr__(self):
        return f'<Product {self.product_name}>'


class Order(db.Model):
    """订单模型"""
    __tablename__ = 'order'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    
    # 客户信息
    customer_name = db.Column(db.String(100), nullable=False)
    
    # 联系人信息（新增）
    contact_person = db.Column(db.String(50))  # 联系人
    contact_phone = db.Column(db.String(20))  # 联系电话
    
    # 订单状态
    status = db.Column(db.String(20), default='quoting')  # quoting/confirmed/pending/producing/completed/cancelled/paused
    
    # 金额相关（新增）
    total_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'))  # 订单总金额
    payment_status = db.Column(db.String(20), default='unpaid')  # unpaid/partial/paid 付款状态
    paid_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'))  # 已付金额
    
    # 生产信息
    production_note = db.Column(db.Text)  # 生产备注
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))  # 分配给的生产人员
    
    # 订单日期
    required_date = db.Column(db.Date)  # 要求完成日期
    order_date = db.Column(db.DateTime, default=datetime.utcnow)  # 下单时间
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    products = db.relationship('Product', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='order', lazy='dynamic', cascade='all, delete-orphan')
    assigned_user = db.relationship('User', foreign_keys=[assigned_to])

    def calculate_total_amount(self):
        """计算订单总金额"""
        total = Decimal('0.00')
        for product in self.products:
            total += product.calculate_amount()
        return total

    def update_payment_status(self):
        """更新付款状态"""
        if self.paid_amount >= self.total_amount:
            self.payment_status = 'paid'
        elif self.paid_amount > 0:
            self.payment_status = 'partial'
        else:
            self.payment_status = 'unpaid'

    def get_status_display(self):
        """获取状态中文显示"""
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

    def get_payment_status_display(self):
        """获取付款状态中文显示"""
        status_map = {
            'unpaid': '未付款',
            'partial': '部分付款',
            'paid': '已付清'
        }
        return status_map.get(self.payment_status, self.payment_status)

    def __repr__(self):
        return f'<Order {self.order_number}>'


class Payment(db.Model):
    """付款记录模型（新增）"""
    __tablename__ = 'payment'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    
    # 付款信息
    amount = db.Column(db.Numeric(10, 2), nullable=False)  # 付款金额
    payment_date = db.Column(db.DateTime, nullable=False)  # 付款日期
    payment_method = db.Column(db.String(20))  # 付款方式：现金/转账/微信/支付宝
    
    # 其他信息
    remark = db.Column(db.String(200))  # 备注
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # 记录人
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_payment_method_display(self):
        """获取付款方式中文显示"""
        method_map = {
            'cash': '现金',
            'transfer': '转账',
            'wechat': '微信',
            'alipay': '支付宝'
        }
        return method_map.get(self.payment_method, self.payment_method)

    def __repr__(self):
        return f'<Payment {self.id} - {self.amount}>'
