# 目录

# 文件目录结构

```text
node_modules/           这个目录是npm package存放地点。是npm i产生的。被.gitignore忽略     
.gitignore              gitu用的，用以标识那些文件、目录要忽略。
.babelrc                babel的配置文件。npm run-script build时u要看这个文件
static/                 一些静态资源文件
static/favicon.ico      网页的favicon文件
package.json            npm的项目配置文件。npm install产生的。
package-lock.json       npm的项目资源版本锁定文件。npm产生的。
requirements.txt        python的依赖文件。
templates               jinja2 template目录。在webpack编译后，会在dist/templates目录中
webpack.config.js       webpack的配置文件
dist/                   webpack产生的文件
```

# Build Client
```bash
# 安装npm软件包，只要做一次
npm install

# build
npm run-script build
```

# 启动服务器
```bash
uvicorn main:app
```