# 雁翎CTF与网络安全攻防实训平台 (YanLing CTF Platform)

## 项目概述

雁翎CTF平台是一个由AI驱动的CTF与网络安全攻防实训平台，旨在为网络安全教育和培训提供全面的解决方案。

## 功能特性

### v1.0 - CTF核心功能
- ✅ 用户注册、登录、认证系统
- ✅ 题目创建、管理和分类
- ✅ Flag提交和验证系统
- ✅ 实时计分板和排行榜
- ✅ 团队协作功能
- ✅ 比赛时间控制
- ✅ 管理员面板

### v2.0 - 容器化实训环境
- 🔄 Docker容器管理
- 🔄 可视化环境编排
- 🔄 动态实训环境部署
- 🔄 环境隔离和安全

### v3.0 - AI智能出题
- 🔄 LLM自动题目生成
- 🔄 难度自适应调整
- 🔄 题目质量智能评估
- 🔄 个性化学习路径

## 技术栈

- **后端**: Python Flask + SQLAlchemy
- **前端**: Vue.js 3 + Element Plus
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **缓存**: Redis
- **任务队列**: Celery
- **容器化**: Docker + Docker Compose
- **AI集成**: OpenAI API / 本地LLM

## 快速开始

### 开发环境部署

```bash
# 克隆项目
git clone https://github.com/your-username/YanLing.git
cd YanLing

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python manage.py init-db

# 启动开发服务器
python app.py
```

### Docker部署

```bash
# 构建并启动服务
docker-compose up -d

# 访问平台
http://localhost:5000
```

## 版本迭代计划

| 版本 | 功能 | 预计时间 | 状态 |
|------|------|----------|------|
| v0.1 | 基础框架 | 1-2周 | 🔄 开发中 |
| v0.2 | 题目系统 | 1-2周 | ⏳ 计划中 |
| v0.3 | 计分板系统 | 1周 | ⏳ 计划中 |
| v0.4 | 团队功能 | 1周 | ⏳ 计划中 |
| v1.0 | CTFd功能完整版 | 1-2周 | ⏳ 计划中 |
| v2.0 | Vulfocus集成 | 3-4周 | ⏳ 计划中 |
| v3.0 | AI自动出题 | 3-4周 | ⏳ 计划中 |

## 贡献指南

欢迎提交Issue和Pull Request来帮助改进项目。

## 许可证

MIT License

## 联系方式

如有问题或建议，请通过Issue联系我们。