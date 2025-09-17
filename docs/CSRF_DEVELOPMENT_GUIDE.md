# CSRF 保护开发规范

## 概述

本文档规定了在 YanLing CTF 平台开发中如何正确使用 CSRF 保护，以防止跨站请求伪造攻击。

## CSRF 保护配置

项目已在 `app/__init__.py` 中启用了 Flask-WTF 的 CSRF 保护：

```python
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()
csrf.init_app(app)
```

## 开发规范

### 1. HTML 表单中的 CSRF 令牌

**所有 POST 表单都必须包含 CSRF 令牌**

#### 正确做法：

```html
<form method="POST">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
    <!-- 其他表单字段 -->
</form>
```

或者使用简化语法：

```html
<form method="POST">
    {{ csrf_token() }}
    <!-- 其他表单字段 -->
</form>
```

#### 错误做法：

```html
<!-- 缺少 CSRF 令牌 - 会导致 400 错误 -->
<form method="POST">
    <!-- 其他表单字段 -->
</form>
```

### 2. AJAX 请求中的 CSRF 令牌

对于 AJAX POST 请求，需要在请求头中包含 CSRF 令牌：

```javascript
// 方法1：在请求头中添加
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", "{{ csrf_token() }}");
        }
    }
});

// 方法2：在 FormData 中添加
const formData = new FormData();
formData.append('csrf_token', '{{ csrf_token() }}');
```

### 3. 模态框表单

模态框中的表单也必须包含 CSRF 令牌：

```html
<div class="modal fade" id="exampleModal">
    <div class="modal-dialog">
        <div class="modal-content">
            <form method="POST">
                {{ csrf_token() }}
                <!-- 表单内容 -->
            </form>
        </div>
    </div>
</div>
```

## 检查清单

在开发新功能时，请确保：

- [ ] 所有 POST 表单都包含 `{{ csrf_token() }}`
- [ ] 所有 AJAX POST 请求都包含 CSRF 令牌
- [ ] 模态框中的表单也包含 CSRF 令牌
- [ ] 动态生成的表单也包含 CSRF 令牌

## 常见错误及解决方案

### 错误1：400 Bad Request - The CSRF token is missing

**原因**：表单中缺少 CSRF 令牌

**解决方案**：在表单中添加 `{{ csrf_token() }}`

### 错误2：400 Bad Request - The CSRF token is invalid

**原因**：CSRF 令牌过期或不匹配

**解决方案**：
1. 刷新页面获取新的令牌
2. 检查令牌是否正确传递

### 错误3：AJAX 请求被拒绝

**原因**：AJAX 请求中缺少 CSRF 令牌

**解决方案**：在请求头或数据中添加 CSRF 令牌

## 测试建议

1. **手动测试**：尝试在没有 CSRF 令牌的情况下提交表单，应该收到 400 错误
2. **自动化测试**：编写测试用例验证 CSRF 保护是否正常工作
3. **代码审查**：在代码审查时检查所有新增的表单是否包含 CSRF 令牌

## 已修复的问题

- ✅ 团队申请批准表单缺少 CSRF 令牌（已修复）
- ✅ 团队申请拒绝表单缺少 CSRF 令牌（已修复）

## 重要经验教训

### CSRF 令牌语法错误案例
**问题描述**：在修复团队申请批准功能时，最初使用了错误的 CSRF 令牌语法

**错误做法**：
```html
<form method="POST">
    {{ csrf_token() }}
    <!-- 表单内容 -->
</form>
```

**正确做法**：
```html
<form method="POST">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
    <!-- 表单内容 -->
</form>
```

**关键教训**：
1. **必须使用 input 标签**：CSRF 令牌必须作为隐藏的 input 字段提交
2. **参考现有实现**：修复前应先查看项目中其他表单的正确实现方式
3. **立即验证**：每次修复后立即测试功能是否正常工作
4. **保持一致性**：所有表单都应使用相同的 CSRF 令牌格式

**验证方法**：
- 提交表单后检查是否还有 400 错误
- 查看服务器日志确认请求成功处理

## 相关文件

- `app/__init__.py` - CSRF 保护配置
- `app/templates/teams/requests.html` - 团队申请管理页面
- 所有包含表单的模板文件

## 参考资料

- [Flask-WTF CSRF Protection](https://flask-wtf.readthedocs.io/en/stable/csrf.html)
- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)