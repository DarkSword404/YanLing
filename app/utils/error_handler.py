"""
错误处理工具类
提供统一的错误处理和用户友好的错误信息
"""

from flask import jsonify, render_template, request, current_app
from werkzeug.exceptions import HTTPException
import traceback
import logging


class ErrorHandler:
    """统一错误处理类"""
    
    @staticmethod
    def handle_validation_error(errors):
        """处理表单验证错误"""
        if request.is_json:
            return jsonify({
                'error': '表单验证失败',
                'details': errors
            }), 400
        
        for error in errors:
            from flask import flash
            flash(error, 'error')
        return None
    
    @staticmethod
    def handle_database_error(e):
        """处理数据库错误"""
        current_app.logger.error(f"数据库错误: {str(e)}")
        
        if request.is_json:
            return jsonify({
                'error': '数据库操作失败，请稍后重试'
            }), 500
        
        from flask import flash
        flash('操作失败，请稍后重试', 'error')
        return None
    
    @staticmethod
    def handle_permission_error():
        """处理权限错误"""
        if request.is_json:
            return jsonify({
                'error': '权限不足'
            }), 403
        
        from flask import flash
        flash('权限不足', 'error')
        return None
    
    @staticmethod
    def handle_not_found_error(resource_name="资源"):
        """处理资源未找到错误"""
        if request.is_json:
            return jsonify({
                'error': f'{resource_name}不存在'
            }), 404
        
        from flask import flash
        flash(f'{resource_name}不存在', 'error')
        return None
    
    @staticmethod
    def handle_rate_limit_error():
        """处理频率限制错误"""
        if request.is_json:
            return jsonify({
                'error': '请求过于频繁，请稍后重试'
            }), 429
        
        from flask import flash
        flash('请求过于频繁，请稍后重试', 'warning')
        return None


def register_error_handlers(app):
    """注册全局错误处理器"""
    
    @app.errorhandler(400)
    def bad_request(error):
        if request.is_json:
            return jsonify({'error': '请求参数错误'}), 400
        return render_template('errors/400.html'), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        if request.is_json:
            return jsonify({'error': '未授权访问'}), 401
        return render_template('errors/401.html'), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        if request.is_json:
            return jsonify({'error': '禁止访问'}), 403
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found(error):
        if request.is_json:
            return jsonify({'error': '页面不存在'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        if request.is_json:
            return jsonify({'error': '请求方法不允许'}), 405
        return render_template('errors/405.html'), 405
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        if request.is_json:
            return jsonify({'error': '请求过于频繁'}), 429
        return render_template('errors/429.html'), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        # 记录错误日志
        app.logger.error(f"服务器内部错误: {str(error)}")
        app.logger.error(traceback.format_exc())
        
        if request.is_json:
            return jsonify({'error': '服务器内部错误'}), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        """处理未捕获的异常"""
        # 如果是HTTP异常，让Flask处理
        if isinstance(e, HTTPException):
            return e
        
        # 记录错误
        app.logger.error(f"未处理的异常: {str(e)}")
        app.logger.error(traceback.format_exc())
        
        if request.is_json:
            return jsonify({'error': '服务器错误，请稍后重试'}), 500
        
        return render_template('errors/500.html'), 500


def safe_execute(func, *args, **kwargs):
    """安全执行函数，捕获异常"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        current_app.logger.error(f"函数执行错误: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return None


def validate_input(data, required_fields, optional_fields=None):
    """验证输入数据"""
    errors = []
    
    # 检查必需字段
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f'{field}不能为空')
    
    # 检查可选字段的格式
    if optional_fields:
        for field, validator in optional_fields.items():
            if field in data and data[field]:
                if not validator(data[field]):
                    errors.append(f'{field}格式不正确')
    
    return errors


def log_user_action(user_id, action, details=None):
    """记录用户操作日志"""
    try:
        log_message = f"用户 {user_id} 执行操作: {action}"
        if details:
            log_message += f" - {details}"
        current_app.logger.info(log_message)
    except Exception as e:
        current_app.logger.error(f"记录用户操作失败: {str(e)}")