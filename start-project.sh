#!/bin/sh

# 启动 PostgreSQL 服务（后台运行）
/docker-entrypoint.sh postgres &

# 等待数据库就绪
echo "等待 PostgreSQL 启动..."
while ! pg_isready -h localhost -p 5432 -U $POSTGRES_USER; do
    sleep 1
done
echo "PostgreSQL 已就绪，启动项目..."

# 运行任务管理系统（确保文件名与你的主程序一致）
python /app/task.py