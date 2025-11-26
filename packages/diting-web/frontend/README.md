# DiTing Web Frontend

DiTing LLM 评估平台的 Web 前端应用。

## 技术栈

- **React 18** - UI框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **TailwindCSS** - UI样式框架
- **React Router** - 路由管理
- **Axios** - HTTP客户端

## 快速开始

### 1. 安装依赖

```bash
cd diting/packages/diting-web/frontend
pnpm install
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# API地址
VITE_API_BASE_URL=http://localhost:8000
```

### 3. 启动开发服务器

```bash
pnpm dev
```

访问：http://localhost:5173

## 项目结构

```
frontend/
├── src/
│   ├── api/              # API客户端
│   ├── components/       # 可复用组件
│   ├── pages/            # 页面组件
│   ├── contexts/         # React Context
│   ├── hooks/            # 自定义Hooks
│   ├── types/            # TypeScript类型定义
│   ├── App.tsx           # 应用入口
│   └── main.tsx          # React入口
├── public/               # 静态资源
└── index.html
```

## 可用命令

```bash
pnpm dev          # 启动开发服务器
pnpm build        # 构建生产版本
pnpm preview      # 预览生产构建
pnpm lint         # 运行ESLint检查
pnpm type-check   # TypeScript类型检查
```

## 主要功能

- ✅ 用户登录认证
- ✅ 数据集管理
- ✅ 评估任务管理
- ✅ 评估器配置
- ✅ 模型管理
- ✅ 提示词管理
- ✅ 统计信息展示

## 开发指南

请参考项目根目录的 [React开发规范](./.cursor/rules/react_frontend.md)。

## 相关文档

- [后端API文档](../backend/README.md)
- [API接口说明](http://localhost:8000/docs)
