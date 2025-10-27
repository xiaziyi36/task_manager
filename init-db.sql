-- 切换到项目数据库（与 Dockerfile 中 ENV POSTGRES_DB 一致）
\c task_db;

-- 创建 tasks 表
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    priority INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    due_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

-- 可选：插入一条测试数据
INSERT INTO tasks (title, description, priority, due_date)
VALUES ('测试任务', '由 init-db.sql 自动创建', 3, '2024-12-31 23:59');