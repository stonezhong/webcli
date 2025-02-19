# Index
* core
    * data
        * [db_models](#db_models)
        * [models](#models)


# core
## data
### db_models
These are SQLAlchemy data models.

| Class                           | Description                              |
| ------------------------------- | ---------------------------------------- |
| DBUser                          | A user                                   |
| DBAction                        | An action                                |
| DBActionResponseChunk           | A chunk of action response               |
| DBThread                        | A thread                                 |
| DBThreadAction                  | Represent a thread has an action         |
| DBActionHandlerConfiguration    | User configuration for a action handler  |

```mermaid
---
title: Web CLI Core Models ER Diagram
---
erDiagram
    DBUser {
        int id PK
        bool is_active
        str email
        int password_version
        str password_hash
    }
    DBAction {
        int id PK
        DBUser user
        str handler_name
        bool is_completed
        datetime created_at
        datetime completed_at
        str title
        dict request
        str raw_text
    }
    DBThread {
        int id PK
        DBUser user
        datetime created_at
        str title
        str description
    }
    DBThreadAction {
        int id PK
        int thread_id
        int action_id
        int display_order
        bool show_answer
        bool show_question
    }
    DBActionResponseChunk {
        int id PK
        int action_id
        int order
        str mime
        str text_content
        str binary_content
    }
    DBActionHandlerConfiguration {
        int id PK
        str action_handler_name
        int user_id
        datetime created_at
        datetime updated_at
        JSON configuration
    }
    

    DBAction }o--|| DBUser : created_by
    DBThread }o--|| DBUser : created_by

    DBThreadAction }o--|| DBThread  : linked-thread
    DBThreadAction }o--|| DBAction  : linked-action

    DBActionResponseChunk }o--|| DBAction : belongs-to

    DBActionHandlerConfiguration }o--|| DBUser: owned-by
    
```

### models
These are Pydandic models.

| Class                           | Description                              |
| ------------------------------- | ---------------------------------------- |
| User                            | A user                                   |
| Action                          | An action                                |
| ActionResponseChunk             | A chunk of action response               |
| Thread                          | A thread                                 |
| ThreadAction                    | Represent a thread has an action         |
| ActionHandlerConfiguration      | User configuration for a action handler  |
