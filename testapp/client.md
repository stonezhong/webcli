# 目录
* 

# 创建一个空的package.json
内容如下
```json
{
    "name": "webcli-demo",
    "version": "1.0.0",
    "description": "Web CLI Demo",
    "main": "index.js",
    "scripts": {
        "build": "webpack"
    },
    "author": "",
    "license": "ISV",
    "devDependencies": {
    },
    "dependencies": {}
}
```

然后第一次安装
```bash
npm install
```
这时，会有文件package-lock.json产生

# 安装一些软件包
因为我们要使用webpack
```bash
npm install webpack webpack-cli --save-dev
```
你会发现有目录node_modules被创建了，同时package.json和package-lock.json也被改动了。

其他一些
```bash
npm install @babel/core --save-dev
npm install @babel/preset-react --save-dev
npm install @babel/preset-env --save-dev
npm install @babel/plugin-transform-class-properties --save-dev
npm install babel-loader html-loader html-webpack-plugin --save-dev
npm install bootstrap --save-dev
npm install bootstrap-icons --save-dev
npm install lodash --save-dev
npm install react-dom --save-dev
npm install react --save-dev
```

# 创建一个webpack.js文件
```javascript

```
