from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models import db, User, Order

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
    
    # 获取新密码（如果有）
    data = request.get_json() if request.is_json else {}
    new_password = data.get('new_password', '123456')
    
    # 如果新密码太短，使用默认密码
    if len(new_password) < 6:
        new_password = '123456'
    
    user.password = generate_password_hash(new_password)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'密码已重置为：{new_password}',
        'password': new_password
    })
    from models import Product
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # 获取筛选参数
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    customer_name = request.args.get('customer_name', '')
    order_no = request.args.get('order_no', '')
    status = request.args.get('status', '')
    assigned_to = request.args.get('assigned_to', '')
    
    # 构建查询
    query = Order.query
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Order.created_at >= start_dt)
        except:
            pass
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Order.created_at < end_dt)
        except:
            pass
    
    if customer_name:
        query = query.filter(Order.customer_name.like(f'%{customer_name}%'))
    
    if order_no:
        query = query.filter(Order.order_no.like(f'%{order_no}%'))
    
    if status:
        query = query.filter(Order.status == status)
    
    if assigned_to:
        query = query.filter(Order.assigned_to == int(assigned_to))
    
    orders = query.order_by(Order.created_at.desc()).all()
    
    # 统计数据
    total_orders = len(orders)
    total_products = sum(len(order.products) for order in orders)
    total_quantity = sum(order.total_quantity for order in orders)
    
    # 按客户统计
    customer_stats = {}
    for order in orders:
        if order.customer_name not in customer_stats:
            customer_stats[order.customer_name] = {
                'order_count': 0,
                'product_count': 0,
                'total_quantity': 0
            }
        customer_stats[order.customer_name]['order_count'] += 1
        customer_stats[order.customer_name]['product_count'] += len(order.products)
        customer_stats[order.customer_name]['total_quantity'] += order.total_quantity
    
    # 按状态统计
    status_stats = {}
    for order in orders:
        status_text = order.get_status_text()
        if status_text not in status_stats:
            status_stats[status_text] = 0
        status_stats[status_text] += 1
    
    # 获取生产人员列表
    workers = User.query.filter_by(role='worker', is_active=True).all()
    
    return render_template('order_overview.html', 
                         orders=orders,
                         workers=workers,
                         total_orders=total_orders,
                         total_products=total_products,
                         total_quantity=total_quantity,
                         customer_stats=customer_stats,
                         status_stats=status_stats,
                         filters={
                             'start_date': start_date,
                             'end_date': end_date,
                             'customer_name': customer_name,
                             'order_no': order_no,
                             'status': status,
                             'assigned_to': assigned_to
                         })


@admin_bp.route('/admin/export_orders')
@login_required
@admin_required
def export_orders():
    """导出订单到Excel"""
    import io
    from models import Product
    from datetime import datetime, timedelta
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    except ImportError:
        flash('请先安装 openpyxl: pip install openpyxl', 'danger')
        return redirect(url_for('admin.order_overview'))
    
    # 获取筛选参数（与order_overview相同）
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    customer_name = request.args.get('customer_name', '')
    order_no = request.args.get('order_no', '')
    status = request.args.get('status', '')
    assigned_to = request.args.get('assigned_to', '')
    
    # 构建查询
    query = Order.query
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Order.created_at >= start_dt)
        except:
            pass
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Order.created_at < end_dt)
        except:
            pass
    
    if customer_name:
        query = query.filter(Order.customer_name.like(f'%{customer_name}%'))
    
    if order_no:
        query = query.filter(Order.order_no.like(f'%{order_no}%'))
    
    if status:
        query = query.filter(Order.status == status)
    
    if assigned_to:
        query = query.filter(Order.assigned_to == int(assigned_to))
    
    orders = query.order_by(Order.created_at.desc()).all()
    
    # 创建Excel工作簿
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "订单明细"
    
    # 样式定义
    header_font = Font(bold=True, size=11)
    header_fill = PatternFill(start_color="667EEA", end_color="667EEA", fill_type="solid")
    header_font_white = Font(bold=True, size=11, color="FFFFFF")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # 写入表头
    headers = ['订单号', '客户名称', '产品名称', '长度(mm)', '宽度(mm)', '厚度(mm)', '颜色', '数量', '状态', '负责人', '创建时间', '备注']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font_white
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border
    
    # 写入数据
    row_num = 2
    for order in orders:
        for i, product in enumerate(order.products):
            ws.cell(row=row_num, column=1, value=order.order_no).border = border
            ws.cell(row=row_num, column=2, value=order.customer_name).border = border
            ws.cell(row=row_num, column=3, value=product.product_name).border = border
            ws.cell(row=row_num, column=4, value=product.length).border = border
            ws.cell(row=row_num, column=5, value=product.width).border = border
            ws.cell(row=row_num, column=6, value=product.thickness if product.thickness else '').border = border
            ws.cell(row=row_num, column=7, value=product.color if product.color else '').border = border
            ws.cell(row=row_num, column=8, value=product.quantity).border = border
            ws.cell(row=row_num, column=9, value=order.get_status_text()).border = border
            ws.cell(row=row_num, column=10, value=order.assignee.name if order.assignee else '未分配').border = border
            ws.cell(row=row_num, column=11, value=order.created_at.strftime('%Y-%m-%d %H:%M')).border = border
            ws.cell(row=row_num, column=12, value=order.remark or '').border = border
            row_num += 1
    
    # 调整列宽
    ws.column_dimensions['A'].width = 18
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 12
    ws.column_dimensions['G'].width = 10
    ws.column_dimensions['H'].width = 10
    ws.column_dimensions['I'].width = 10
    ws.column_dimensions['J'].width = 12
    ws.column_dimensions['K'].width = 18
    ws.column_dimensions['L'].width = 30
    
    # 创建客户汇总表
    ws2 = wb.create_sheet("客户汇总")
    
    # 汇总表头
    summary_headers = ['客户名称', '订单数', '产品数', '总数量']
    for col, header in enumerate(summary_headers, 1):
        cell = ws2.cell(row=1, column=col, value=header)
        cell.font = header_font_white
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border
    
    # 汇总数据
    customer_stats = {}
    for order in orders:
        if order.customer_name not in customer_stats:
            customer_stats[order.customer_name] = {'orders': 0, 'products': 0, 'quantity': 0}
        customer_stats[order.customer_name]['orders'] += 1
        customer_stats[order.customer_name]['products'] += len(order.products)
        customer_stats[order.customer_name]['quantity'] += order.total_quantity
    
    row_num = 2
    for customer, stats in sorted(customer_stats.items()):
        ws2.cell(row=row_num, column=1, value=customer).border = border
        ws2.cell(row=row_num, column=2, value=stats['orders']).border = border
        ws2.cell(row=row_num, column=3, value=stats['products']).border = border
        ws2.cell(row=row_num, column=4, value=stats['quantity']).border = border
        row_num += 1
    
    # 调整汇总表列宽
    ws2.column_dimensions['A'].width = 20
    ws2.column_dimensions['B'].width = 12
    ws2.column_dimensions['C'].width = 12
    ws2.column_dimensions['D'].width = 12
    
    # 保存到内存
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    # 生成文件名
    filename = f"订单导出_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    from flask import send_file
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )
