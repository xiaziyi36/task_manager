import psycopg2
from psycopg2 import OperationalError, Error
from dotenv import load_dotenv
import os
import datetime

# 加载环境变量
load_dotenv()


def create_connection():
    """创建PostgreSQL数据库连接"""
    connection = None
    try:
        connection = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            port=os.getenv("DB_PORT", 5432)
        )
        print("数据库连接成功")
    except OperationalError as err:
        print(f"数据库连接错误: {err}")
    return connection


def initialize_table(connection):
    """初始化任务表（如果不存在）"""
    create_table_query = """
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
    """
    try:
        cursor = connection.cursor()
        cursor.execute(create_table_query)
        connection.commit()
        print("任务表初始化成功")
    except Error as err:
        print(f"初始化表结构失败: {err}")
        connection.rollback()


def add_task(connection):
    """添加新任务"""
    title = input("请输入任务标题: ").strip()
    if not title:
        print("任务标题不能为空!")
        return

    description = input("请输入任务描述 (可选): ").strip() or None
    priority = input("请输入优先级 (1-最高, 2-高, 3-中, 4-低, 5-最低, 默认3): ").strip()
    priority = int(priority) if priority and priority in ['1', '2', '3', '4', '5'] else 3

    due_date = input("请输入截止日期 (格式: YYYY-MM-DD HH:MM, 可选): ").strip()
    due_date = due_date if due_date else None

    query = """
    INSERT INTO tasks (title, description, priority, due_date)
    VALUES (%s, %s, %s, %s)
    RETURNING id;
    """

    try:
        cursor = connection.cursor()
        cursor.execute(query, (title, description, priority, due_date))
        task_id = cursor.fetchone()[0]  # 获取返回的ID
        connection.commit()
        print(f"任务添加成功! 任务ID: {task_id}")
    except Error as err:
        print(f"添加任务失败: {err}")
        connection.rollback()


def view_tasks(connection):
    """查询任务"""
    print("\n查询选项:")
    print("1. 查看所有任务")
    print("2. 查看未完成任务")
    print("3. 查看已完成任务")
    print("4. 按优先级查询")
    print("5. 按截止日期查询")

    choice = input("请选择查询方式 (1-5): ").strip()
    query = "SELECT * FROM tasks"
    params = []

    if choice == '1':
        query += " ORDER BY created_at DESC"
    elif choice == '2':
        query += " WHERE is_completed = FALSE ORDER BY due_date ASC NULLS LAST"
    elif choice == '3':
        query += " WHERE is_completed = TRUE ORDER BY completed_at DESC NULLS LAST"
    elif choice == '4':
        priority = input("请输入要查询的优先级 (1-5): ").strip()
        if priority in ['1', '2', '3', '4', '5']:
            query += " WHERE priority = %s ORDER BY due_date ASC NULLS LAST"
            params.append(priority)
        else:
            print("无效的优先级!")
            return
    elif choice == '5':
        date_str = input("请输入要查询的截止日期 (格式: YYYY-MM-DD): ").strip()
        query += " WHERE DATE(due_date) = %s ORDER BY due_date ASC"
        params.append(date_str)
    else:
        print("无效的选择!")
        return

    try:
        cursor = connection.cursor()
        cursor.execute(query, params)
        tasks = cursor.fetchall()

        if not tasks:
            print("没有找到符合条件的任务!")
            return

        print("\n" + "=" * 60)
        print(f"找到 {len(tasks)} 个任务:")
        print("-" * 60)
        for task in tasks:
            status = "✓ 已完成" if task[4] else "○ 未完成"
            priority_map = {1: "最高", 2: "高", 3: "中", 4: "低", 5: "最低"}
            due_date = task[5].strftime("%Y-%m-%d %H:%M") if task[5] else "无"

            print(f"ID: {task[0]}")
            print(f"标题: {task[1]}")
            print(f"描述: {task[2] or '无'}")
            print(f"优先级: {priority_map[task[3]]}")
            print(f"状态: {status}")
            print(f"截止日期: {due_date}")
            print(f"创建时间: {task[6].strftime('%Y-%m-%d %H:%M')}")
            print("-" * 60)
    except Error as err:
        print(f"查询任务失败: {err}")


def update_task(connection):
    """更新任务状态"""
    task_id = input("请输入要更新的任务ID: ").strip()
    if not task_id.isdigit():
        print("无效的任务ID!")
        return

    print("\n更新选项:")
    print("1. 标记任务为已完成")
    print("2. 标记任务为未完成")
    print("3. 修改任务标题")
    print("4. 修改任务截止日期")

    choice = input("请选择更新方式 (1-4): ").strip()
    query = ""
    params = []

    if choice == '1':
        query = """
        UPDATE tasks 
        SET is_completed = TRUE, completed_at = CURRENT_TIMESTAMP 
        WHERE id = %s
        """
        params = [task_id]
    elif choice == '2':
        query = """
        UPDATE tasks 
        SET is_completed = FALSE, completed_at = NULL 
        WHERE id = %s
        """
        params = [task_id]
    elif choice == '3':
        new_title = input("请输入新的任务标题: ").strip()
        if not new_title:
            print("任务标题不能为空!")
            return
        query = "UPDATE tasks SET title = %s WHERE id = %s"
        params = [new_title, task_id]
    elif choice == '4':
        new_date = input("请输入新的截止日期 (格式: YYYY-MM-DD HH:MM): ").strip()
        query = "UPDATE tasks SET due_date = %s WHERE id = %s"
        params = [new_date, task_id]
    else:
        print("无效的选择!")
        return

    try:
        cursor = connection.cursor()
        cursor.execute(query, params)
        connection.commit()
        if cursor.rowcount > 0:
            print("任务更新成功!")
        else:
            print("未找到该任务ID或未发生变更!")
    except Error as err:
        print(f"更新任务失败: {err}")
        connection.rollback()


def delete_task(connection):
    """删除任务"""
    task_id = input("请输入要删除的任务ID: ").strip()
    if not task_id.isdigit():
        print("无效的任务ID!")
        return

    confirm = input(f"确定要删除ID为 {task_id} 的任务吗? (y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消删除!")
        return

    query = "DELETE FROM tasks WHERE id = %s"
    try:
        cursor = connection.cursor()
        cursor.execute(query, (task_id,))
        connection.commit()
        if cursor.rowcount > 0:
            print("任务删除成功!")
        else:
            print("未找到该任务ID!")
    except Error as err:
        print(f"删除任务失败: {err}")
        connection.rollback()


def main():
    """主函数"""
    connection = create_connection()
    if not connection:
        print("无法连接到数据库，程序退出!")
        return

    # 初始化表结构
    initialize_table(connection)

    print("=" * 50)
    print("欢迎使用命令行任务管理系统")
    print("=" * 50)

    while True:
        print("\n功能菜单:")
        print("1. 添加新任务")
        print("2. 查看任务列表")
        print("3. 更新任务状态")
        print("4. 删除任务")
        print("5. 退出系统")

        choice = input("请选择功能 (1-5): ").strip()

        if choice == '1':
            add_task(connection)
        elif choice == '2':
            view_tasks(connection)
        elif choice == '3':
            update_task(connection)
        elif choice == '4':
            delete_task(connection)
        elif choice == '5':
            print("感谢使用，再见!")
            break
        else:
            print("无效的选择，请重新输入!")

    connection.close()


if __name__ == "__main__":
    main()