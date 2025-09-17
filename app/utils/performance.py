"""
性能优化工具类
提供缓存、数据库查询优化等功能
"""

from functools import wraps
from flask import current_app, request, g
from flask_caching import Cache
import time
import hashlib
import json

# 初始化缓存
cache = Cache()


def init_cache(app):
    """初始化缓存配置"""
    cache.init_app(app)


def cache_key_generator(*args, **kwargs):
    """生成缓存键"""
    key_data = {
        'args': args,
        'kwargs': kwargs,
        'user_id': getattr(g, 'user_id', None),
        'path': request.path if request else None
    }
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached_query(timeout=300, key_prefix='query'):
    """数据库查询缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{cache_key_generator(*args, **kwargs)}"
            
            # 尝试从缓存获取
            result = cache.get(cache_key)
            if result is not None:
                current_app.logger.debug(f"缓存命中: {cache_key}")
                return result
            
            # 执行查询
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # 记录慢查询
            if execution_time > 1.0:
                current_app.logger.warning(
                    f"慢查询检测: {func.__name__} 耗时 {execution_time:.2f}s"
                )
            
            # 缓存结果
            cache.set(cache_key, result, timeout=timeout)
            current_app.logger.debug(f"缓存设置: {cache_key}")
            
            return result
        return wrapper
    return decorator


def performance_monitor(func):
    """性能监控装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # 记录性能数据
            current_app.logger.info(
                f"性能监控: {func.__name__} 执行时间 {execution_time:.3f}s"
            )
            
            # 如果执行时间过长，记录警告
            if execution_time > 2.0:
                current_app.logger.warning(
                    f"性能警告: {func.__name__} 执行时间过长 {execution_time:.3f}s"
                )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            current_app.logger.error(
                f"性能监控: {func.__name__} 执行失败，耗时 {execution_time:.3f}s，错误: {str(e)}"
            )
            raise
    
    return wrapper


class DatabaseOptimizer:
    """数据库查询优化器"""
    
    @staticmethod
    def paginate_query(query, page=1, per_page=20, max_per_page=100):
        """安全的分页查询"""
        # 限制每页最大数量
        per_page = min(per_page, max_per_page)
        
        # 执行分页查询
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return {
            'items': pagination.items,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': pagination.page,
            'per_page': pagination.per_page,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next,
            'prev_num': pagination.prev_num,
            'next_num': pagination.next_num
        }
    
    @staticmethod
    def batch_query(model, ids, batch_size=100):
        """批量查询优化"""
        results = []
        
        # 分批查询
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_results = model.query.filter(model.id.in_(batch_ids)).all()
            results.extend(batch_results)
        
        return results
    
    @staticmethod
    def optimize_joins(query, *relationships):
        """优化关联查询"""
        for relationship in relationships:
            query = query.options(relationship)
        return query


class MemoryOptimizer:
    """内存优化器"""
    
    @staticmethod
    def chunked_processing(items, chunk_size=1000):
        """分块处理大量数据"""
        for i in range(0, len(items), chunk_size):
            yield items[i:i + chunk_size]
    
    @staticmethod
    def lazy_loading(func):
        """延迟加载装饰器"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 只在需要时才执行函数
            return lambda: func(*args, **kwargs)
        return wrapper


def clear_cache_by_pattern(pattern):
    """根据模式清除缓存"""
    try:
        # 这里需要根据具体的缓存后端实现
        # Redis示例：
        # cache.cache._write_client.delete(*cache.cache._write_client.keys(pattern))
        current_app.logger.info(f"清除缓存模式: {pattern}")
    except Exception as e:
        current_app.logger.error(f"清除缓存失败: {str(e)}")


def get_cache_stats():
    """获取缓存统计信息"""
    try:
        # 这里需要根据具体的缓存后端实现
        return {
            'status': 'active',
            'backend': cache.config.get('CACHE_TYPE', 'unknown')
        }
    except Exception as e:
        current_app.logger.error(f"获取缓存统计失败: {str(e)}")
        return {'status': 'error', 'error': str(e)}


# 常用的缓存键前缀
CACHE_KEYS = {
    'USER_PROFILE': 'user_profile',
    'CHALLENGE_LIST': 'challenge_list',
    'SCOREBOARD': 'scoreboard',
    'STATISTICS': 'statistics',
    'CATEGORY_LIST': 'category_list'
}