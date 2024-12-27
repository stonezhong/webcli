# 目录
* [文件目录结构](#文件目录结构)
* [build客户端](#build客户端)
* [启动服务器](#启动服务器)

# 文件目录结构

```text
.
├── dist                                webpack build产生的目录，每次build都会重新创建里面的所有文件和子目录里的文件
│   ├── admin.js                        从javascripts/index.js中获得，通过babel将ES 6转换成ES 5
│   ├── index.js                        从javascripts/admin.js中获得，通过babel将ES 6转换成ES 5
│   └── templates
│       └── index.html                  从templates/index.html中得到，通过webpack的plugin HtmlWebpackPlugin
├── javascripts                         javascript源代码
│   ├── admin.js                        顶层代码，在webpack中的entry栏目中出现
│   ├── index.jsx                       顶层代码，在webpack中的entry栏目中出现
│   └── app.js                          模块代码，被顶层代码或者其他模块调用
├── main.py                             python程序的主入口
├── package.json                        npm 项目定义文件
├── package-lock.json                   npm 项目的锁定文件，用于锁定npm package的版本
├── README.md
├── requirements.txt                    python的需要的package清单
├── static                              静态文件目录
│   └── favicon.ico
├── templates                           jinja template目录，次目录不直接expose在web中，一般要通过webpack编译后在dist/templates中产生
│   ├── admin.html                      admin页面的模板
│   └── index.html                      index页面的模板
└── webpack.config.js                   webpack的配置文件



# Build Client
```bash
# 安装npm软件包，只要做一次
npm install

# build
npm run-script build
```

# build客户端
```bash
npm run-script build
```

# 启动服务器
```bash
uvicorn main:app
```

# 在JavaScript中Import css
```javascript
// 这个css文件将被import到最终的HTML文件中。
import './App.css';
// or 
import './App.scss';
```
