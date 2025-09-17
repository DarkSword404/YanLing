// 雁翎CTF平台 - 主要JavaScript功能

document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有功能
    initializeTooltips();
    initializeAnimations();
    initializeFormValidation();
    initializeLoadingStates();
    initializeNotifications();
});

// 初始化工具提示
function initializeTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// 初始化动画效果
function initializeAnimations() {
    // 为卡片添加淡入动画
    const cards = document.querySelectorAll('.card, .challenge-card, .stats-card');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add('fade-in');
    });

    // 滚动时的动画效果
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('slide-up');
            }
        });
    }, observerOptions);

    // 观察所有需要动画的元素
    document.querySelectorAll('.card, .jumbotron, .stats-card').forEach(el => {
        observer.observe(el);
    });
}

// 表单验证
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // 显示第一个错误字段
                const firstInvalid = form.querySelector(':invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                    showNotification('请检查表单中的错误信息', 'warning');
                }
            }
            
            form.classList.add('was-validated');
        });
    });

    // 实时验证
    const inputs = document.querySelectorAll('input, textarea, select');
    inputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.checkValidity()) {
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            } else {
                this.classList.remove('is-valid');
                this.classList.add('is-invalid');
            }
        });
    });
}

// 加载状态管理
function initializeLoadingStates() {
    // 为所有表单提交按钮添加加载状态
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    
    submitButtons.forEach(button => {
        const form = button.closest('form');
        if (form) {
            form.addEventListener('submit', function() {
                if (form.checkValidity()) {
                    showLoadingState(button);
                }
            });
        }
    });

    // AJAX请求的加载状态
    const ajaxButtons = document.querySelectorAll('[data-ajax]');
    ajaxButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            showLoadingState(this);
            
            // 模拟AJAX请求
            setTimeout(() => {
                hideLoadingState(this);
            }, 2000);
        });
    });
}

// 显示加载状态
function showLoadingState(button) {
    const originalText = button.innerHTML;
    button.dataset.originalText = originalText;
    button.innerHTML = '<span class="loading"></span> 处理中...';
    button.disabled = true;
}

// 隐藏加载状态
function hideLoadingState(button) {
    button.innerHTML = button.dataset.originalText;
    button.disabled = false;
}

// 通知系统
function initializeNotifications() {
    // 创建通知容器
    if (!document.getElementById('notification-container')) {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 350px;
        `;
        document.body.appendChild(container);
    }
}

// 显示通知
function showNotification(message, type = 'info', duration = 5000) {
    const container = document.getElementById('notification-container');
    const notification = document.createElement('div');
    
    const typeClasses = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    };
    
    const icons = {
        'success': 'fas fa-check-circle',
        'error': 'fas fa-exclamation-circle',
        'warning': 'fas fa-exclamation-triangle',
        'info': 'fas fa-info-circle'
    };
    
    notification.className = `alert ${typeClasses[type]} alert-dismissible fade show`;
    notification.style.cssText = 'margin-bottom: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.15);';
    
    notification.innerHTML = `
        <i class="${icons[type]}"></i>
        <span class="ms-2">${message}</span>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.appendChild(notification);
    
    // 自动移除通知
    if (duration > 0) {
        setTimeout(() => {
            if (notification.parentNode) {
                notification.classList.remove('show');
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.remove();
                    }
                }, 150);
            }
        }, duration);
    }
}

// 确认对话框
function showConfirmDialog(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// 复制到剪贴板
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showNotification('已复制到剪贴板', 'success');
        }).catch(() => {
            fallbackCopyToClipboard(text);
        });
    } else {
        fallbackCopyToClipboard(text);
    }
}

function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showNotification('已复制到剪贴板', 'success');
    } catch (err) {
        showNotification('复制失败，请手动复制', 'error');
    }
    
    document.body.removeChild(textArea);
}

// 格式化时间
function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    const minute = 60 * 1000;
    const hour = minute * 60;
    const day = hour * 24;
    
    if (diff < minute) {
        return '刚刚';
    } else if (diff < hour) {
        return Math.floor(diff / minute) + '分钟前';
    } else if (diff < day) {
        return Math.floor(diff / hour) + '小时前';
    } else {
        return date.toLocaleDateString('zh-CN');
    }
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

// 节流函数
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

// 全局错误处理
window.addEventListener('error', function(e) {
    console.error('JavaScript错误:', e.error);
    showNotification('页面出现错误，请刷新重试', 'error');
});

// 网络状态监测
window.addEventListener('online', function() {
    showNotification('网络连接已恢复', 'success');
});

window.addEventListener('offline', function() {
    showNotification('网络连接已断开', 'warning');
});

// 导出全局函数
window.CTF = {
    showNotification,
    showConfirmDialog,
    copyToClipboard,
    formatTime,
    debounce,
    throttle,
    showLoadingState,
    hideLoadingState
};