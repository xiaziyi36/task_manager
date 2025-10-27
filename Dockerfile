# 基础镜像：使用本地已有的 postgis/postgis 镜像
FROM postgis/postgis:10-2.5-alpine

# 维护者信息
LABEL maintainer="task-manager"

# 1. 安装系统依赖（删除libpq，避免版本冲突）
# postgresql-dev已包含libpq，无需单独安装
RUN apk add --no-cache \
    python3 \
    py3-pip \
    python3-dev \
    gcc \
    musl-dev \
    postgresql-dev \  # 这里的反斜杠后不能有注释，否则失效
    && ln -sf python3 /usr/bin/python \
    && ln -sf pip3 /usr/bin/pip

# 2. 设置工作目录
WORKDIR /app

# 3. 复制依赖清单并安装
COPY requirements.txt .
RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --upgrade pip \
    -r requirements.txt

# 4. 复制项目文件
COPY . .

# 5. 复制数据库初始化脚本
COPY ./init-db.sql /docker-entrypoint-initdb.d/

# 6. 设置环境变量
ENV POSTGRES_USER=task_user \
    POSTGRES_PASSWORD=task_pwd \
    POSTGRES_DB=task_db \
    DB_HOST=localhost \
    DB_PORT=5432 \
    DB_USER=task_user \
    DB_PASSWORD=task_pwd \
    DB_NAME=task_db

# 7. 暴露端口
EXPOSE 5432

# 8. 配置启动脚本
COPY ./start-project.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/start-project.sh

# 启动命令
CMD ["start-project.sh"]
