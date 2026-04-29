# -*- coding: utf-8 -*-
"""
订单路由模块
包含订单创建、列表、详情等功能
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Order, Product, User, Payment
from decimal import Decimal
from datetime import datetime, date
import json

order_bp = Blueprint('order', __name__)


def generate_order_number():
    """生成订单号：日期+序号"""
    today = date.today()
    today_str = today.strftime('%Y%m%d')
    
    # 查找今天最新的订单号
    latest_order = Order.query.filter(
        Order.order_number.like(f'ORD{today_str}%')
    ).order_by(Order.order_number.desc()).first()
    
    if latest_order:
        # 提取序号并+1
        try:
            seq = int(latest_order.order_number[-4:]) + 1
        except:
            seq = 1
    else:
        seq = 1
    
    return f'ORD{today_str}{seq:04d}'


@order_bp.route('/create_order', methods=['GET', 'POST'])
@login_required
def create_order():
    """创建订单页面"""
    # 权限控制：仅跟单员和管理员可见
    if current_user.role not in ['admin', 'admin_assistant', 'clerks']:
        flash('您没有权限创建订单', 'danger')
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        try:
            # 获取表单数据
            customer_name = request.form.get('customer_name', '').strip()
            contact_person = request.form.get('contact_person', '').strip()
            contact_phone = request.form.get('contact_phone', '').strip()
            required_date_str = request.form.get('required_date', '')
            production_note = request.form.get('production_note', '').strip()
            
            # 验证必填字段
            if not customer_name:
                flash('客户名称不能为空', 'danger')
                return redirect(url_for('order.create_order'))
            
            # 创建订单
            order = Order(
                order_number=generate_order_number(),
                customer_name=customer_name,
                contact_person=contact_person,
                contact_phone=contact_phone,
                status='quoting',  # 默认报价状态
                production_note=production_note,
                created_by=current_user.id
            )
            
            # 处理要求完成日期
            if required_date_str:
                try:
                    order.required_date = datetime.strptime(required_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            db.session.add(order)
            db.session.flush()  # 获取order.id
            
            # 处理产品明细
            products_data = []
            index = 0
            while True:
                product_name = request.form.get(f'product_name_{index}', '').strip()
                if not product_name:
                    # 检查是否还有其他产品
                    has_more = False
                    for i in range(index + 1, index + 10):
                        if request.form.get(f'product_name_{i}', '').strip():
                            has_more = True
                            break
                    if not has_more:
                        break
                    index += 1
                    continue
                
                # 获取产品字段
                quantity = request.form.get(f'quantity_{index}', '1')
                unit_price = request.form.get(f'unit_price_{index}', '0')
                unit = request.form.get(f'unit_{index}', '件')
                color = request.form.get(f'color_{index}', '')
                size = request.form.get(f'size_{index}', '')
                weight = request.form.get(f'weight_{index}', '')
                material = request.form.get(f'material_{index}', '')
                craft = request.form.get(f'craft_{index}', '')
                other_req = request.form.get(f'other_requirements_{index}', '')
                remark = request.form.get(f'remark_{index}', '')
                
                # 转换为数值
                try:
                    quantity = int(quantity) if quantity else 1
                except ValueError:
                    quantity = 1
                
                try:
                    unit_price = Decimal(str(unit_price)) if unit_price else Decimal('0.00')
                except ValueError:
                    unit_price = Decimal('0.00')
                
                # 计算金额
                amount = Decimal(str(quantity)) * unit_price
                
                # 创建产品
                product = Product(
                    order_id=order.id,
                    product_name=product_name,
                    quantity=quantity,
                    unit_price=unit_price,
                    unit=unit,
                    amount=amount,
                    color=color,
                    size=size,
                    weight=weight,
                    material=material,
                    craft=craft,
                    other_requirements=other_req,
                    remark=remark
                )
                db.session.add(product)
                
                products_data.append({
                    'product_name': product_name,
                    'quantity': quantity,
                    'unit_price': float(unit_price),
                    'amount': float(amount)
                })
                
                index += 1
            
            # 计算订单总金额
            order.total_amount = sum(item['amount'] for item in products_data)
            order.payment_status = 'unpaid'
            order.paid_amount = Decimal('0.00')
            
            db.session.commit()
            
            flash(f'订单创建成功！订单号：{order.order_number}', 'success')
            return redirect(url_for('order.order_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'创建订单失败：{str(e)}', 'danger')
            return redirect(url_for('order.create_order'))
    
    # GET请求：渲染创建订单页面
    return render_template('create_order.html')


@order_bp.route('/order_list')
@login_required
def order_list():
    """订单列表"""
    # 获取筛选参数
    status_filter = request.args.get('status', '')
    search_keyword = request.args.get('keyword', '')
    
    # 构建查询
    query = Order.query
    
    if status_filter:
        query = query.filter(Order.status == status_filter)
    
    if search_keyword:
        query = query.filter(
            db.or_(
                Order.order_number.like(f'%{search_keyword}%'),
                Order.customer_name.like(f'%{search_keyword}%')
            )
        )
    
    # 排序：最新在前
    orders = query.order_by(Order.created_at.desc()).all()
    
    # 获取所有状态选项
    status_choices = [
        ('quoting', '报价中'),
        ('confirmed', '已确认'),
        ('pending', '待生产'),
        ('producing', '进行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('paused', '已暂停')
    ]
    
    return render_template('order_list.html', 
                         orders=orders,
                         status_choices=status_choices,
                         current_status=status_filter,
                         search_keyword=search_keyword)


@order_bp.route('/quoting_list')
@login_required
def quoting_list():
    """报价管理列表（仅显示状态=quoting的订单）"""
    if current_user.role not in ['admin', 'admin_assistant', 'clerks']:
        flash('您没有权限访问此页面', 'danger')
        return redirect(url_for('main.dashboard'))
    
    orders = Order.query.filter_by(status='quoting').order_by(Order.created_at.desc()).all()
    return render_template('quoting_list.html', orders=orders)


@order_bp.route('/order_detail/<int:order_id>')
@login_required
def order_detail(order_id):
    """订单详情"""
    order = Order.query.get_or_404(order_id)
    products = order.products.all()
    
    # 计算订单统计
    total_quantity = sum(p.quantity for p in products)
    total_amount = sum(float(p.amount or 0) for p in products)
    
    return render_template('order_detail.html',
                         order=order,
                         products=products,
                         total_quantity=total_quantity,
                         total_amount=total_amount)


@order_bp.route('/order_update_status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    """更新订单状态"""
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status', '')
    
    valid_statuses = ['quoting', 'confirmed', 'pending', 'producing', 'completed', 'cancelled', 'paused']
    
    if new_status not in valid_statuses:
        return jsonify({'success': False, 'message': '无效的状态'})
    
    order.status = new_status
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'状态已更新为：{order.get_status_display()}'
    })


@order_bp.route('/order_assign/<int:order_id>', methods=['POST'])
@login_required
def assign_order(order_id):
    """分配订单给生产人员"""
    if current_user.role not in ['admin', 'admin_assistant', 'clerks']:
        return jsonify({'success': False, 'message': '没有权限'})
    
    order = Order.query.get_or_404(order_id)
    user_id = request.form.get('user_id')
    
    if user_id:
        order.assigned_to = int(user_id)
    else:
        order.assigned_to = None
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': '订单已分配'})


@order_bp.route('/my_tasks')
@login_required
def my_tasks():
    """我的生产任务（生产人员）"""
    if current_user.role != 'production':
        flash('此页面仅生产人员可用', 'warning')
        return redirect(url_for('main.dashboard'))
    
    orders = Order.query.filter(
        Order.assigned_to == current_user.id,
        Order.status.in_(['pending', 'producing', 'paused'])
    ).order_by(Order.required_date.asc()).all()
    
    return render_template('my_tasks.html', orders=orders)


# ===== 付款相关路由 =====

@order_bp.route('/payment_records')
@login_required
def payment_records():
    """付款记录列表（管理员可见）"""
    if current_user.role != 'admin':
        flash('此页面仅管理员可见', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # 获取筛选参数
    order_number = request.args.get('order_number', '').strip()
    
    query = Payment.query
    
    if order_number:
        query = query.join(Order).filter(Order.order_number.like(f'%{order_number}%'))
    
    payments = query.order_by(Payment.payment_date.desc()).all()
    
    return render_template('payment_records.html', payments=payments)


@order_bp.route('/add_payment/<int:order_id>', methods=['GET', 'POST'])
@login_required
def add_payment(order_id):
    """添加付款记录"""
    if current_user.role != 'admin':
        flash('此页面仅管理员可见', 'danger')
        return redirect(url_for('main.dashboard'))
    
    order = Order.query.get_or_404(order_id)
    
    if request.method == 'POST':
        try:
            amount_str = request.form.get('amount', '0')
            payment_date_str = request.form.get('payment_date', '')
            payment_method = request.form.get('payment_method', '')
            remark = request.form.get('remark', '').strip()
            
            # 验证
            try:
                amount = Decimal(str(amount_str))
                if amount <= 0:
                    flash('付款金额必须大于0', 'danger')
                    return redirect(url_for('order.add_payment', order_id=order_id))
            except ValueError:
                flash('无效的付款金额', 'danger')
                return redirect(url_for('order.add_payment', order_id=order_id))
            
            # 检查是否超过未付金额
            unpaid_amount = order.total_amount - order.paid_amount
            if amount > unpaid_amount:
                flash(f'付款金额不能超过未付金额 ({unpaid_amount})', 'warning')
                return redirect(url_for('order.add_payment', order_id=order_id))
            
            # 解析日期
            try:
                payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d')
            except ValueError:
                payment_date = datetime.now()
            
            # 创建付款记录
            payment = Payment(
                order_id=order_id,
                amount=amount,
                payment_date=payment_date,
                payment_method=payment_method,
                remark=remark,
                created_by=current_user.id
            )
            
            # 更新订单已付金额和付款状态
            order.paid_amount += amount
            order.update_payment_status()
            
            db.session.add(payment)
            db.session.commit()
            
            flash(f'付款记录已添加！金额：{amount}', 'success')
            return redirect(url_for('order.order_detail', order_id=order_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'添加付款记录失败：{str(e)}', 'danger')
    
    return render_template('add_payment.html', order=order)


@order_bp.route('/all_orders')
@login_required
def all_orders():
    """全部订单（管理员）"""
    if current_user.role != 'admin':
        flash('此页面仅管理员可见', 'danger')
        return redirect(url_for('main.dashboard'))
    
    # 获取筛选参数
    status_filter = request.args.get('status', '')
    search_keyword = request.args.get('keyword', '')
    
    query = Order.query
    
    if status_filter:
        query = query.filter(Order.status == status_filter)
    
    if search_keyword:
        query = query.filter(
            db.or_(
                Order.order_number.like(f'%{search_keyword}%'),
                Order.customer_name.like(f'%{search_keyword}%')
            )
        )
    
    orders = query.order_by(Order.created_at.desc()).all()
    
    status_choices = [
        ('quoting', '报价中'),
        ('confirmed', '已确认'),
        ('pending', '待生产'),
        ('producing', '进行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('paused', '已暂停')
    ]
    
    return render_template('all_orders.html',
                         orders=orders,
                         status_choices=status_choices,
                         current_status=status_filter,
                         search_keyword=search_keyword)


# ===== API接口 =====

@order_bp.route('/api/calculate_amount', methods=['POST'])
@login_required
def api_calculate_amount():
    """计算金额API"""
    data = request.get_json()
    quantity = int(data.get('quantity', 0))
    unit_price = float(data.get('unit_price', 0))
    
    amount = quantity * unit_price
    
    return jsonify({
        'success': True,
        'amount': round(amount, 2)
    })


@order_bp.route('/api/get_order_products/<int:order_id>')
@login_required
def api_get_order_products(order_id):
    """获取订单产品列表API"""
    order = Order.query.get_or_404(order_id)
    products = order.products.all()
    
    products_data = []
    for p in products:
        products_data.append({
            'id': p.id,
            'product_name': p.product_name,
            'quantity': p.quantity,
            'unit_price': float(p.unit_price or 0),
            'amount': float(p.amount or 0),
            'unit': p.unit,
            'color': p.color,
            'size': p.size
        })
    
    return jsonify({
        'success': True,
        'products': products_data,
        'total_amount': float(order.total_amount or 0)
    })
