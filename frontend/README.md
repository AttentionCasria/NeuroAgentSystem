# MedicalRAGLLM Frontend

医疗RAG（检索增强生成）大语言模型前端项目

## 项目简介

这是一个基于 Vue 3 开发的医疗领域智能问答系统前端应用。系统支持用户注册登录、与医疗AI助手进行对话交流、查看历史对话记录等功能。采用流式响应技术，提供流畅的实时对话体验。

## 技术栈

- **框架**: Vue 3 (Composition API)
- **构建工具**: Vite 7
- **状态管理**: Pinia (支持持久化)
- **路由**: Vue Router 4
- **HTTP 客户端**: Axios
- **表单组件**: VueForm
- **样式**: Normalize.css
- **开发工具**: ESLint + Prettier

## 功能特性

- ✅ 用户注册与登录
- ✅ 用户信息管理（头像上传、密码修改）
- ✅ 智能医疗问答对话
- ✅ 流式响应实时显示
- ✅ 历史对话记录管理
- ✅ 对话标题列表展示
- ✅ 对话删除功能

## 项目结构

```
frontend/
├── src/
│   ├── api/              # API 接口定义
│   │   ├── talk.js       # 对话相关接口
│   │   └── user.js       # 用户相关接口
│   ├── components/       # 组件
│   │   ├── form/         # 表单组件
│   │   ├── svg/          # SVG 图标组件
│   │   ├── AvatarUpload.vue
│   │   ├── UserDialog.vue
│   │   └── ...
│   ├── router/           # 路由配置
│   ├── stores/           # Pinia 状态管理
│   ├── utils/            # 工具函数
│   ├── views/            # 页面视图
│   │   ├── login.vue     # 登录页
│   │   └── talk.vue      # 对话页
│   ├── App.vue
│   └── main.js
├── public/               # 静态资源
├── dist/                 # 构建输出
└── vite.config.js        # Vite 配置
```

## 环境要求

- Node.js: `^20.19.0 || >=22.12.0`
- npm 或 yarn

## 安装与运行

### 1. 安装依赖

```bash
npm install
```

### 2. 开发环境运行

```bash
npm run dev
```

项目将在 `http://localhost:5173` 启动，并自动打开浏览器。

### 3. 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist/` 目录。

### 4. 预览生产构建

```bash
npm run preview
```

## 开发脚本

- `npm run dev` - 启动开发服务器
- `npm run build` - 构建生产版本
- `npm run preview` - 预览生产构建
- `npm run lint` - 运行 ESLint 并自动修复
- `npm run format` - 使用 Prettier 格式化代码

## 配置说明

### 后端 API 配置

后端服务默认运行在 `http://localhost:8080`，可在 `vite.config.js` 中修改代理配置：

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8080',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
  },
}
```

### 环境变量

如需配置环境变量，可在项目根目录创建 `.env` 文件：

```env
VITE_API_BASE_URL=http://localhost:8080
```

## API 接口

### 用户相关

- `POST /api/user/login` - 用户登录
- `POST /api/user/register` - 用户注册
- `POST /api/user/logOut` - 退出登录
- `GET /api/user/showInfo` - 获取用户信息
- `PUT /api/user/showInfo/changeKey` - 修改用户信息
- `POST /api/user/upload` - 上传头像

### 对话相关

- `GET /api/user/title` - 获取对话标题列表
- `GET /api/user/ques/getQues/:talkId` - 获取历史对话内容
- `POST /api/user/ques/getQues` - 继续对话（发送问题）
- `POST /api/user/ques/newGetQues` - 新建对话
- `POST /api/user/ques/streamingQues` - 流式问答接口
- `DELETE /api/user/deleteTalk/:talkId` - 删除对话

## 浏览器支持

- Chrome (最新版本)
- Firefox (最新版本)
- Safari (最新版本)
- Edge (最新版本)

## 开发规范

- 使用 ESLint 进行代码检查
- 使用 Prettier 进行代码格式化
- 遵循 Vue 3 Composition API 最佳实践
- 组件命名采用 PascalCase
- 文件命名采用 camelCase

## 许可证

本项目为私有项目。

## 联系方式

如有问题或建议，请联系项目维护者。
