from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models import db, User, Order

admin_bp = Blueprint('admin', __name__)

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

@admin_bp.route('/admin')
@login_required
@admin_required
def index():
    # 统计信息
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_orders = Order.query.count()
    
    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'total_orders': total_orders
    }
    
    return render_template('admin.html', stats=stats)

@admin_bp.route('/admin/users')
@login_required
@admin_required
def user_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('user_list.html', users=users)

@admin_bp.route('/admin/user/add', methods=['POST'])
@login_required
@admin_required
def add_user():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    name = request.form.get('name', '').strip()
    role = request.form.get('role', '')
    
    # 验证
    if not all([username, password, name, role]):
        flash('请填写所有必填字段', 'danger')
        return redirect(url_for('admin.user_list'))
    
    if role not in ['admin', 'sales', 'worker']:
        flash('无效的角色', 'danger')
        return redirect(url_for('admin.user_list'))
    
    # 检查用户名是否已存在
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

@admin_bp.route('/admin/user/<int:user_id>/toggle_status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    
    # 不能禁用自己
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': '不能禁用自己的账号'})
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = '启用' if user.is_active else '禁用'
    return jsonify({'success': True, 'message': f'用户已{status}'})

@admin_bp.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # 不能删除自己
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': '不能删除自己的账号'})
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '用户已删除'})

@admin_bp.route('/admin/order/assign', methods=['POST'])
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

@admin_bp.route('/admin/all_orders')
@login_required
@admin_required
def all_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    workers = User.query.filter_by(role='worker', is_active=True).all()
    return render_template('admin_orders.html', orders=orders, workers=workers)

@admin_bp.route('/admin/user/<int:user_id>/reset_password', methods=['POST'])
@login_required
@admin_required
def reset_user_password(user_id):
    user = User.query.get_or_404(user_id)
    
    # 重置密码为默认密码 123456
    default_password = '123456'
    user.password = generate_password_hash(default_password)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'密码已重置为：{default_password}',
        'password': default_password
    })