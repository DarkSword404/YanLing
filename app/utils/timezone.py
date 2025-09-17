from datetime import datetime, timezone, timedelta

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))

def get_beijing_time():
    """获取当前北京时间"""
    return datetime.now(BEIJING_TZ)

def utc_to_beijing(utc_dt):
    """将UTC时间转换为北京时间"""
    if utc_dt is None:
        return None
    
    # 如果是naive datetime，假设它是UTC时间
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    
    # 转换为北京时间
    return utc_dt.astimezone(BEIJING_TZ)

def format_beijing_time(dt, format_str='%Y-%m-%d %H:%M'):
    """格式化北京时间显示"""
    if dt is None:
        return ''
    
    # 如果是UTC时间，先转换为北京时间
    if dt.tzinfo is None or dt.tzinfo == timezone.utc:
        dt = utc_to_beijing(dt)
    
    return dt.strftime(format_str)