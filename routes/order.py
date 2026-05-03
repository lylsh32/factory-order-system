import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Order, Product, Attachment
from datetime import datetime
from decimal import Decimal

order_bp = Blueprint('order', __name__)

def allowed_file(filename):
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'dwg', 'dxf', 'pdf'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@order_bp.route('/')
@order_bp.route('/dashboard')
@login_required
def dashboard():
    # 获取统计数据
    if current_user.role == 'admin':
        total_orders = Order.query.count()
        pending_orders = Order.query.filter(Order.status.in_(['quoting', 'confirmed', 'pending'])).count()
        producing_orders = Order.query.filter_by(status='producing').count()
        completed_orders = Order.query.filter_by(status='completed').count()
        recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    elif current_user.role == 'sales':
        total_orders = Order.query.filter_by(created_by=current_user.id).count()
        pending_orders = Order.query.filter_by(created_by=current_user.id).filter(Order.status.in_(['quoting', 'confirmed', 'pending'])).count()
        producing_orders = Order.query.filter_by(created_by=current_user.id, status='producing').count()
        completed_orders = Order.query.filter_by(created_by=current_user.id, status='completed').count()
        recent_orders = Order.query.filter_by(created_by=current_user.id).order_by(Order.created_at.desc()).limit(10).all()
    else:  # worker
        from sqlalchemy import or_
        total_orders = Order.query.filter(
            (Order.assigned_to == current_user.id) | (Order.assigned_to == None)
        ).count()
        pending_orders = Order.query.filter(
            (Order.assigned_to == current_user.id) | (Order.assigned_to == None),
            Order.status.in_(['pending', 'confirmed'])
        ).count()
        producing_orders = Order.query.filter(
            (Order.assigned_to == current_user.id) | (Order.assigned_to == None),
            Order.status == 'producing'
        ).count()
        completed_orders = Order.query.filter_by(assigned_to=current_user.id, status='completed').count()
        recent_orders = Order.query.filter(
            (Order.assigned_to == current_user.id) | (Order.assigned_to == None)
        ).order_by(Order.created_at.desc()).limit(10).all()
    
    stats = {
        'total': total_orders,
        'pending': pending_orders,
        'producing': producing_orders,
        'completed': completed_orders
    }
    
    return render_template('dashboard.html', stats=stats, recent_orders=recent_orders)

@order_bp.route('/orders')
@login_required
def order_list():
    status_filter = request.args.get('status', '')
    
    if current_user.role == 'admin':
        query = Order.query
    elif current_user.role == 'sales':
        query = Order.query.filter_by(created_by=current_user.id)
    else:
        query = Order.query.filter(
            (Order.assigned_to == current_user.id) | (Order.assigned_to == None)
        )
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    orders = query.order_by(Order.created_at.desc()).all()
    
    return render_template('order_list.html', orders=orders, status_filter=status_filter)

@order_bp.route('/create_order', methods=['GET', 'POST'])
@login_required
def create_order():
    if current_user.role not in ['admin', 'sales']:
        flash('您没有权限执行此操作', 'danger')
        return redirect(url_for('order.dashboard'))
    
    # 获取统计数据（用于侧边栏）
    if current_user.role == 'admin':
        total_orders = Order.query.count()
        pending_orders = Order.query.filter(Order.status.in_(['quoting', 'confirmed', 'pending'])).count()
        producing_orders = Order.query.filter_by(status='producing').count()
        completed_orders = Order.query.filter_by(status='completed').count()
    elif current_user.role == 'sales':
        total_orders = Order.query.filter_by(created_by=current_user.id).count()
        pending_orders = Order.query.filter_by(created_by=current_user.id).filter(Order.status.in_(['quoting', 'confirmed', 'pending'])).count()
        producing_orders = Order.query.filter_by(created_by=current_user.id, status='producing').count()
        completed_orders = Order.query.filter_by(created_by=current_user.id, status='completed').count()
    else:
        total_orders = 0
        pending_orders = 0
        producing_orders = 0
        completed_orders = 0
    
    stats = {
        'total': total_orders,
        'pending': pending_orders,
        'producing': producing_orders,
        'completed': completed_orders
    }
    
    if request.method == 'POST':
        customer_name = request.form.get('customer_name', '').strip()
        contact_person = customer_name
        contact_phone = request.form.get('contact_phone', '').strip()    # 新增
        remark = request.form.get('remark', '').strip()
        assigned_to = request.form.get('assigned_to', '')
        
        # 获取所有产品数据
        product_names = request.form.getlist('product_name[]')
        lengths = request.form.getlist('length[]')
        widths = request.form.getlist('width[]')
        thicknesses = request.form.getlist('thickness[]')
        colors = request.form.getlist('color[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')  # 新增
        units = request.form.getlist('unit[]')              # 新增
        screenshots = request.form.getlist('screenshot[]')
        
        # 验证必填字段
        if not customer_name:
            flash('请填写客户名称', 'danger')
            from models import User
            workers = User.query.filter_by(role='worker', is_active=True).all() if current_user.role == 'admin' else []
            return render_template('create_order.html', workers=workers, stats=stats)
        
        if not product_names or len(product_names) == 0:
            flash('请至少添加一个产品', 'danger')
            from models import User
            workers = User.query.filter_by(role='worker', is_active=True).all() if current_user.role == 'admin' else []
            return render_template('create_order.html', workers=workers, stats=stats)
        
        # 验证每个产品
        products_data = []
        total_amount = Decimal('0.00')
        
        for i in range(len(product_names)):
            if not product_names[i].strip():
                flash(f'第{i+1}个产品名称不能为空', 'danger')
                from models import User
                workers = User.query.filter_by(role='worker', is_active=True).all() if current_user.role == 'admin' else []
                return render_template('create_order.html', workers=workers, stats=stats)
            
            try:
                length = float(lengths[i])
                width = float(widths[i])
                quantity = int(quantities[i])
            except (ValueError, IndexError):
                flash(f'第{i+1}个产品的尺寸或数量格式不正确', 'danger')
                from models import User
                workers = User.query.filter_by(role='worker', is_active=True).all() if current_user.role == 'admin' else []
                return render_template('create_order.html', workers=workers, stats=stats)
            
            if quantity <= 0:
                flash(f'第{i+1}个产品的数量必须大于0', 'danger')
                from models import User
                workers = User.query.filter_by(role='worker', is_active=True).all() if current_user.role == 'admin' else []
                return render_template('create_order.html', workers=workers, stats=stats)
            
            # 厚度（可选）
            thickness = None
            try:
                if i < len(thicknesses) and thicknesses[i]:
                    thickness = float(thicknesses[i])
            except ValueError:
                pass
            
            # 颜色（可选）
            color = colors[i].strip() if i < len(colors) else None
            
            # 单价和金额（新增）
            unit_price = Decimal('0.00')
            try:
                if i < len(unit_prices) and unit_prices[i]:
                    unit_price = Decimal(str(unit_prices[i]))
            except:
                pass
            
            amount = Decimal(str(quantity)) * unit_price
            total_amount += amount
            
            # 单位
            unit = units[i] if i < len(units) and units[i] else '件'
            
            # 截图（可选）
            screenshot = screenshots[i] if i < len(screenshots) else None
            
            products_data.append({
                'product_name': product_names[i].strip(),
                'length': length,
                'width': width,
                'thickness': thickness,
                'color': color,
                'quantity': quantity,
                'unit_price': unit_price,
                'amount': amount,
                'unit': unit,
                'screenshot': screenshot if screenshot else None
            })
        
        # 生成订单号：ORD-YYYYMMDD-XXX
        today = datetime.now().strftime('%Y%m%d')
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_orders_count = Order.query.filter(Order.created_at >= today_start).count()
        order_no = f"ORD-{today}-{str(today_orders_count + 1).zfill(3)}"
        
        # 创建订单
        order = Order(
            order_no=order_no,
            customer_name=customer_name,
            contact_person=contact_person,      # 新增
            contact_phone=contact_phone,        # 新增
            total_amount=total_amount,          # 新增
            remark=remark if remark else None,
            status='quoting',  # 默认报价状态
            created_by=current_user.id,
            assigned_to=int(assigned_to) if assigned_to else None
        )
        
        db.session.add(order)
        db.session.flush()
        
        # 创建产品并处理附件
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        
        for i, product_data in enumerate(products_data):
            product = Product(
                order_id=order.id,
                product_name=product_data['product_name'],
                length=product_data['length'],
                width=product_data['width'],
                thickness=product_data['thickness'],
                color=product_data['color'],
                quantity=product_data['quantity'],
                unit_price=product_data['unit_price'],    # 新增
                amount=product_data['amount'],            # 新增
                unit=product_data['unit'],                # 新增
                screenshot=product_data['screenshot']
            )
            db.session.add(product)
            db.session.flush()
            
            # 处理附件
            # 附件处理终极方案：不管前端传什么字段名，直接把所有文件按顺序分配
            all_files = []
            for key in request.files.keys():
                for f in request.files.getlist(key):
                    if f and f.filename:
                        all_files.append(f)
            
            # 按产品顺序分配文件
            if i < len(all_files):
                file = all_files[i]
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    new_filename = f"{order.id}_{product.id}_{timestamp}_{filename}"
                    filepath = os.path.join(upload_folder, new_filename)
                    file.save(filepath)
                    attachment = Attachment(
                        product_id=product.id,
                        filename=filename,
                        filepath=new_filename
                    )
                    db.session.add(attachment)
        
        db.session.commit()
        flash(f'订单创建成功！订单号：{order.order_no}', 'success')
        return redirect(url_for('order.order_detail', order_id=order.id))
    
    # GET请求
    from models import User
    workers = User.query.filter_by(role='worker', is_active=True).all() if current_user.role == 'admin' else []
    
    return render_template('create_order.html', workers=workers, stats=stats)

@order_bp.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    
    if current_user.role == 'worker' and order.assigned_to not in [current_user.id, None]:
        flash('您没有权限查看此订单', 'danger')
        return redirect(url_for('order.order_list'))
    
    return render_template('order_detail.html', order=order)


@order_bp.route("/order/<int:order_id>/overview")
@login_required
def order_overview(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("order_overview.html", order=order)
@order_bp.route('/order/<int:order_id>/update_status', methods=['POST'])
@login_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status', '')
    
    if current_user.role == 'worker':
        if order.assigned_to != current_user.id:
            return jsonify({'success': False, 'message': '您没有权限操作此订单'})
        if new_status not in ['producing', 'completed', 'paused']:
            return jsonify({'success': False, 'message': '无效的状态操作'})
    
    if current_user.role == 'sales':
        if order.created_by != current_user.id:
            return jsonify({'success': False, 'message': '您没有权限操作此订单'})
        # 跟单员可以确认报价、取消、暂停
        if new_status not in ['confirmed', 'cancelled', 'paused', 'pending']:
            return jsonify({'success': False, 'message': '跟单员只能确认报价、取消或暂停订单'})
    
    # 状态流转验证
    valid_transitions = {
        'quoting': ['confirmed', 'cancelled'],          # 报价中可确认或取消
        'confirmed': ['pending', 'cancelled'],          # 已确认可转待生产或取消
        'pending': ['producing', 'cancelled', 'paused'],
        'producing': ['completed', 'paused'],
        'paused': ['producing', 'cancelled'],
        'completed': [],
        'cancelled': []
    }
    
    if new_status not in valid_transitions.get(order.status, []):
        return jsonify({'success': False, 'message': f'无法从 {order.get_status_text()} 转换为目标状态'})
    
    order.status = new_status
    order.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'订单状态已更新为 {order.get_status_text()}'})

@order_bp.route('/order/<int:order_id>/claim', methods=['POST'])
@login_required
def claim_order(order_id):
    """生产人员认领订单"""
    order = Order.query.get_or_404(order_id)
    
    if current_user.role != 'worker':
        return jsonify({'success': False, 'message': '只有生产人员可以认领订单'})
    
    if order.assigned_to is not None:
        return jsonify({'success': False, 'message': '此订单已被分配'})
    
    order.assigned_to = current_user.id
    order.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'您已成功认领订单 #{order.id}'})

@order_bp.route('/download/<int:attachment_id>')
@login_required
def download_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    product = attachment.product
    order = product.order
    
    if current_user.role == 'worker' and order.assigned_to != current_user.id:
        flash('您没有权限下载此文件', 'danger')
        return redirect(url_for('order.order_list'))
    
    upload_folder = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(upload_folder, attachment.filepath, as_attachment=True, download_name=attachment.filename)

@order_bp.route('/order/<int:order_id>/delete', methods=['POST'])
@login_required
def delete_order(order_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': '只有管理员可以删除订单'})
    
    order = Order.query.get_or_404(order_id)
    
    upload_folder = current_app.config['UPLOAD_FOLDER']
    for product in order.products:
        for attachment in product.attachments:
            try:
                filepath = os.path.join(upload_folder, attachment.filepath)
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception:
                pass
    
    db.session.delete(order)
    db.session.commit()
    flash('订单已删除', 'success')
    
    return jsonify({'success': True, 'message': '订单已删除'})

@order_bp.route('/order/<int:order_id>/qrcode')
@login_required
def order_qrcode(order_id):
    """生成订单二维码"""
    import qrcode
    from io import BytesIO
    import base64
    
    order = Order.query.get_or_404(order_id)
    preview_url = url_for('order.order_preview', order_no=order.order_no, _external=True)
    
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(preview_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return jsonify({
        'success': True,
        'qrcode': f'data:image/png;base64,{img_str}',
        'preview_url': preview_url
    })

@order_bp.route('/preview/<order_no>')
def order_preview(order_no):
    """订单预览页面（无需登录）"""
    order = Order.query.filter_by(order_no=order_no).first_or_404()
    return render_template('order_preview.html', order=order)

@order_bp.route('/payment_records')
@login_required
def payment_records():
    """付款记录列表"""
    if current_user.role != 'admin':
        flash('您没有权限访问此页面', 'danger')
        return redirect(url_for('order.dashboard'))
    
    # 获取筛选参数
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    payment_method_filter = request.args.get('payment_method', '')
    
    from models import Payment
    
    query = Payment.query.order_by(Payment.payment_date.desc())
    
    # 日期筛选
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Payment.payment_date >= start)
        except:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            end = end.replace(hour=23, minute=59, second=59)
            query = query.filter(Payment.payment_date <= end)
        except:
            pass
    
    # 付款方式筛选
    if payment_method_filter:
        query = query.filter(Payment.payment_method == payment_method_filter)
    
    payments = query.all()
    
    # 统计
    total_amount = sum(p.amount for p in payments)
    
    return render_template('payment_records.html', 
                          payments=payments,
                          total_amount=total_amount,
                          start_date=start_date,
                          end_date=end_date,
                          payment_method_filter=payment_method_filter)
