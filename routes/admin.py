from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models import db, User, Order
from datetime import datetime, timedelta
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """装饰器：检查是否为管理员"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash('您没有权限访问此页面', 'danger')
            return redirect(url_for('order.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def index():
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_orders = Order.query.count()
    
    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'total_orders': total_orders
    }
    
    return render_template('admin.html', stats=stats)

@admin_bp.route('/users')
@login_required
@admin_required
def user_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('user_list.html', users=users)

@admin_bp.route('/user/add', methods=['POST'])
@login_required
@admin_required
def add_user():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    name = request.form.get('name', '').strip()
    role = request.form.get('role', '')
    
    if not all([username, password, name, role]):
        flash('请填写所有必填字段', 'danger')
        return redirect(url_for('admin.user_list'))
    
    if role not in ['admin', 'sales', 'worker']:
        flash('无效的角色', 'danger')
        return redirect(url_for('admin.user_list'))
    
    if User.query.filter_by(username=username).first():
        flash('用户名已存在', 'danger')
        return redirect(url_for('admin.user_list'))
    
    user = User(
        username=username,
        password=generate_password_hash(password),
        name=name,
        role=role,
        is_active=True
    )
    
    db.session.add(user)
    db.session.commit()
    
    flash(f'用户 {name} 创建成功', 'success')
    return redirect(url_for('admin.user_list'))

@admin_bp.route('/user/<int:user_id>/toggle_status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': '不能禁用自己的账号'})
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = '启用' if user.is_active else '禁用'
    return jsonify({'success': True, 'message': f'用户已{status}'})

@admin_bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': '不能删除自己的账号'})
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '用户已删除'})

@admin_bp.route('/order/assign', methods=['POST'])
@login_required
@admin_required
def assign_order():
    order_id = request.form.get('order_id', type=int)
    worker_id = request.form.get('worker_id', type=int)
    
    order = Order.query.get_or_404(order_id)
    
    if worker_id:
        worker = User.query.get_or_404(worker_id)
        if worker.role != 'worker':
            return jsonify({'success': False, 'message': '只能分配给生产人员'})
    
    order.assigned_to = worker_id if worker_id else None
    db.session.commit()
    
    return jsonify({'success': True, 'message': '订单分配成功'})

@admin_bp.route('/all_orders')
@login_required
@admin_required
def all_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    workers = User.query.filter_by(role='worker', is_active=True).all()
    return render_template('admin_orders.html', orders=orders, workers=workers)

@admin_bp.route('/user/<int:user_id>/reset_password', methods=['POST'])
@login_required
@admin_required
def reset_user_password(user_id):
    user = User.query.get_or_404(user_id)
    
    data = request.get_json() if request.is_json else {}
    new_password = data.get('new_password', '123456')
    
    if len(new_password) < 6:
        new_password = '123456'
    
    user.password = generate_password_hash(new_password)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'密码已重置为：{new_password}',
        'password': new_password
    })

@admin_bp.route('/order_overview')
@login_required
@admin_required
def order_overview():
    from models import Product
    
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    customer_name = request.args.get('customer_name', '')
    
    query = Order.query
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Order.created_at >= start)
        except:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Order.created_at < end)
        except:
            pass
    
    if customer_name:
        query = query.filter(Order.customer_name.like(f'%{customer_name}%'))
    
    orders = query.order_by(Order.created_at.desc()).all()
    
    total_quantity = sum(o.total_quantity for o in orders)
    
    return render_template('order_overview.html', 
                          orders=orders, 
                          total_quantity=total_quantity,
                          start_date=start_date,
                          end_date=end_date,
                          customer_name=customer_name)

@admin_bp.route('/export_orders')
@login_required
@admin_required
def export_orders():
    from io import BytesIO
    from openpyxl import Workbook
    
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    customer_name = request.args.get('customer_name', '')
    
    query = Order.query
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Order.created_at >= start)
        except:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Order.created_at < end)
        except:
            pass
    
    if customer_name:
        query = query.filter(Order.customer_name.like(f'%{customer_name}%'))
    
    orders = query.order_by(Order.created_at.desc()).all()
    
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "订单明细"
    
    headers = ['订单号', '客户名称', '产品名称', '长度', '宽度', '厚度', '颜色', '数量', '状态', '负责人', '创建时间']
    ws1.append(headers)
    
    for order in orders:
        for product in order.products:
            ws1.append([
                order.order_no,
                order.customer_name,
                product.product_name,
                product.length,
                product.width,
                product.thickness or '',
                product.color or '',
                product.quantity,
                order.get_status_text(),
                order.assignee.name if order.assignee else '未分配',
                order.created_at.strftime('%Y-%m-%d %H:%M')
            ])
    
    ws2 = wb.create_sheet("客户汇总")
    ws2.append(['客户名称', '订单数', '总数量'])
    
    customer_stats = {}
    for order in orders:
        if order.customer_name not in customer_stats:
            customer_stats[order.customer_name] = {'orders': 0, 'quantity': 0}
        customer_stats[order.customer_name]['orders'] += 1
        customer_stats[order.customer_name]['quantity'] += order.total_quantity
    
    for customer, stats in customer_stats.items():
        ws2.append([customer, stats['orders'], stats['quantity']])
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'订单导出_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )
