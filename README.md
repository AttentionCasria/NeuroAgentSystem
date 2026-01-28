# 1. 要打开redis





# 2. 下面是mysql建表语句

```mysql
use medai;

create table user (
    id int unsigned not null auto_increment primary key comment '这是主键',
    name varchar(15) not null unique comment '这是名字',
    password varchar(255) not null comment '这是密码哈希值',
    image varchar(255) comment '这是头像',
    create_time varchar(20) not null comment '创建时间',
    update_time varchar(20) not null comment '更新时间'
);

create table talk(
    id int unsigned not null unique auto_increment primary key comment '这是主键',
    user_id int unsigned not null comment '这是哪个用户',
    title text not null comment '这是标题',
    content text not null comment '这是主要内容',
    create_time varchar(20) not null comment '创建时间',
    update_time varchar(20) not null comment '更新时间'
);
create table cont(
    id int unsigned not null unique auto_increment primary key comment '这是主键',
    user_id int unsigned not null comment '这是哪个用户',
    talk_id int unsigned not null comment '这是哪个用户的哪条对话',
    content text not null comment '这是存储的内容',
    create_time varchar(20) not null comment '创建时间'
);



INSERT INTO `user` (name, password, create_time, update_time)
VALUES ('darkside', '123456', DATE_FORMAT(NOW(), '%Y-%m-%d %H:%i:%s'), DATE_FORMAT(NOW(), '%Y-%m-%d %H:%i:%s'));

select t.title from talk t;
```



