from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

auth_bp = Blueprint('auth', __name__)

def init_login_manager(app):
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    return login_manager

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('order.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('请输入用户名和密码', 'danger')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            if not user.is_active:
                flash('账号已被禁用，请联系管理员', 'warning')
                return render_template('login.html')
            
            login_user(user, remember=True)
            flash(f'欢迎回来，{user.name}！', 'success')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('order.dashboard'))
        
        flash('用户名或密码错误', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已安全退出', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # 验证
        if not all([old_password, new_password, confirm_password]):
            flash('请填写所有字段', 'danger')
            return redirect(url_for('auth.change_password'))
        
        # 验证旧密码
        if not check_password_hash(current_user.password, old_password):
            flash('原密码错误', 'danger')
            return redirect(url_for('auth.change_password'))
        
        # 验证新密码长度
        if len(new_password) < 6:
            flash('新密码至少需要6个字符', 'danger')
            return redirect(url_for('auth.change_password'))
        
        # 验证两次密码一致
        if new_password != confirm_password:
            flash('两次输入的新密码不一致', 'danger')
            return redirect(url_for('auth.change_password'))
        
        # 更新密码
        current_user.password = generate_password_hash(new_password)
        db.session.commit()
        
        flash('密码修改成功，请重新登录', 'success')
        logout_user()
        return redirect(url_for('auth.login'))
    
    return render_template('change_password.html')