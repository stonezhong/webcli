# 系统设计
```
core/data                   数据访问层。详细内容请看DataAccessor类
                            这层的接口使用Model (Pydandic Model, not SQLAlchemy Model)
-------------------------------------------------------------------------------------------------
core/service                服务层                            
```

# 系统结构图
```mermaid
flowchart TD
    classDef greenbox fill:green

    db[(数据库)]
    dal[
        数据访问层
        DataAccessor
    ]:::greenbox
    sl[
        服务层
    ]

    db<-->dal<-->sl

```

# 发送action response的设计
```mermaid
flowchart TD
    classDef greenbox fill:green

    wsh[
        Web Socket Handler
        async function for client1
    ]
    subgraph teq[
        Thread Event Queues
    ]
        q1[async Queue for client1]
        q2[async Queue for client2]
    end
    ah[
        action handler
        running in thread pool
    ]
    arc[Action Response Chunk]
    wc[Web Client -- client1]

    wc --1:create--> q1
    ah --2:create--> arc --3:push event--> q1 --4:pop event,pull--> wsh --5:notify via websocket--> wc
    arc --3:push event--> q2
```
* 1: 当用户浏览thread页面时，会建立websocket连接，发送client_id和thread_id，服务器会创建Thread Event Queues，并且在其中为client1创建一个async Queue
* 2: 当action handler要输出时，会创建一个`ActionResponseChunk`对象
* 3: 针对刚才创建的`ActionResponseChunk`，创建一个event，放入`Thread Event Queue`
* 4: 服务器中，每个websocket有一个async 函数，循环poll event (从`Thread Event Queue`)
* 5: 一旦获得消息，则将消息通过Web Socket发送给浏览器
