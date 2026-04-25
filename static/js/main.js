// 工厂排单系统 - 全局JavaScript

// Toast通知
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 250px; animation: slideIn 0.3s ease';
    toast.innerHTML = `<i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-circle'} me-2"></i>${message}`;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 确认对话框
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 移动端菜单切换
document.addEventListener('DOMContentLoaded', function() {
    // 自动关闭移动端侧边栏点击外部
    document.addEventListener('click', function(event) {
        const sidebar = document.getElementById('sidebar');
        const mobileToggle = document.querySelector('.mobile-toggle');
        
        if (window.innerWidth < 992 && 
            sidebar && 
            sidebar.classList.contains('active') &&
            !sidebar.contains(event.target) &&
            !mobileToggle.contains(event.target)) {
            sidebar.classList.remove('active');
        }
    });
});

// 键盘快捷键
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K: 打开搜索（如果需要）
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        // 可以扩展为搜索功能
    }
    
    // Escape: 关闭模态框
    if (e.key === 'Escape') {
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        });
    }
});

// 表格行点击高亮
document.addEventListener('click', function(e) {
    if (e.target.closest('table tbody tr')) {
        const rows = e.target.closest('tbody').querySelectorAll('tr');
        rows.forEach(row => row.classList.remove('table-active'));
        e.target.closest('tr').classList.add('table-active');
    }
});

// 自动隐藏提示消息
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});
