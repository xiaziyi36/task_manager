import psycopg2
from psycopg2 import OperationalError, Error
from dotenv import load_dotenv
import os
import datetime
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler

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


def add_task(conn):
    # 1. 获取用户输入（标题、描述等，与测试中的模拟输入对应）
    title = input("请输入任务标题: ")
    description = input("请输入任务描述 (可选): ")
    # ... 其他输入获取逻辑 ...

    # 2. 执行INSERT语句（关键修正点）
    cursor = conn.cursor()
    # 正确的INSERT语句，需包含所有任务字段，并通过RETURNING id返回任务ID
    insert_sql = """
        INSERT INTO tasks (title, description, priority, due_date, created_at, is_completed)
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, FALSE)
        RETURNING id;  # 适配PostgreSQL的ID返回方式
    """
    # 绑定参数（避免SQL注入，参数顺序与字段对应）
    cursor.execute(insert_sql, (title, description, priority, due_date))

    # 3. 获取返回的任务ID并提示成功
    task_id = cursor.fetchone()[0]
    conn.commit()
    print(f"任务添加成功! 任务ID: {task_id}")
    cursor.close()


    try:
        cursor = connection.cursor()
        cursor.execute(query, (title, description, priority, due_date))
        task_id = cursor.fetchone()[0]  # 获取返回的ID
        connection.commit()
        print(f"任务添加成功! 任务ID: {task_id}")
        
        # 如果有足够的历史数据，预测新任务的完成概率
        if has_enough_data(connection):
            probability = predict_completion_probability(connection, task_id)
            print(f"预测该任务按时完成的概率: {probability:.1%}")
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
    print("6. 查看任务完成概率预测")

    choice = input("请选择查询方式 (1-6): ").strip()
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
    elif choice == '6':
        if has_enough_data(connection):
            view_predicted_probabilities(connection)
        else:
            print("数据不足，无法进行预测。至少需要10个已完成或逾期的任务。")
        return
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


def has_enough_data(connection):
    """检查是否有足够的数据进行模型训练"""
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM tasks 
            WHERE (is_completed = TRUE AND completed_at IS NOT NULL) 
            OR (is_completed = FALSE AND due_date < CURRENT_TIMESTAMP)
        """)
        count = cursor.fetchone()[0]
        return count >= 10  # 至少需要10个已完成或逾期未完成的任务
    except Error as err:
        print(f"检查数据时出错: {err}")
        return False


def train_model(connection):
    """训练任务完成预测模型"""
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT 
                priority,
                EXTRACT(EPOCH FROM (due_date - created_at)) / 3600 AS hours_available,
                CASE 
                    WHEN is_completed = TRUE AND completed_at <= due_date THEN 1  -- 按时完成
                    WHEN is_completed = TRUE AND completed_at > due_date THEN 0  -- 逾期完成
                    WHEN is_completed = FALSE AND due_date < CURRENT_TIMESTAMP THEN 0  -- 逾期未完成
                    ELSE NULL  -- 排除未到期且未完成的任务
                END AS success
            FROM tasks
            WHERE due_date IS NOT NULL  -- 只考虑有截止日期的任务
        """)
        
        data = cursor.fetchall()
        # 过滤掉无效数据
        valid_data = [row for row in data if row[2] is not None and row[1] is not None and row[1] > 0]
        
        if len(valid_data) < 10:
            return None, None
        
        # 准备特征和目标变量
        X = np.array([[row[0], row[1]] for row in valid_data])  # 优先级和可用小时数
        y = np.array([row[2] for row in valid_data])  # 是否成功完成
        
        # 数据标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # 划分训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
        
        # 训练线性回归模型
        model = LinearRegression()
        model.fit(X_train, y_train)
        
        # 评估模型
        y_pred = model.predict(X_test)
        y_pred_binary = [1 if p >= 0.5 else 0 for p in y_pred]
        accuracy = accuracy_score(y_test, y_pred_binary)
        print(f"模型训练完成，准确率: {accuracy:.1%}")
        
        return model, scaler
        
    except Error as err:
        print(f"训练模型时出错: {err}")
        return None, None


def predict_completion_probability(connection, task_id):
    """预测指定任务的完成概率"""
    model, scaler = train_model(connection)
    if not model or not scaler:
        return 0.0
        
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT priority, due_date, created_at 
            FROM tasks 
            WHERE id = %s
        """, (task_id,))
        
        task = cursor.fetchone()
        if not task or not task[1]:  # 没有截止日期的任务无法预测
            return 0.5  # 默认值
            
        priority, due_date, created_at = task
        
        # 计算剩余可用小时数
        now = datetime.datetime.now(datetime.timezone.utc)
        hours_remaining = (due_date - now).total_seconds() / 3600
        
        if hours_remaining <= 0:
            return 0.0  # 已经逾期
            
        # 准备特征数据
        X = np.array([[priority, hours_remaining]])
        X_scaled = scaler.transform(X)
        
        # 预测概率
        probability = model.predict(X_scaled)[0]
        # 确保概率在0-1之间
        return max(0.0, min(1.0, probability))
        
    except Error as err:
        print(f"预测任务完成概率时出错: {err}")
        return 0.0


def view_predicted_probabilities(connection):
    """查看所有未完成任务的完成概率预测"""
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, title, priority, due_date, created_at 
            FROM tasks 
            WHERE is_completed = FALSE AND due_date IS NOT NULL
            ORDER BY due_date ASC
        """)
        
        tasks = cursor.fetchall()
        if not tasks:
            print("没有可预测的未完成任务!")
            return
            
        model, scaler = train_model(connection)
        if not model or not scaler:
            return
            
        print("\n" + "=" * 60)
        print("任务完成概率预测:")
        print("-" * 60)
        
        now = datetime.datetime.now(datetime.timezone.utc)
        
        for task in tasks:
            task_id, title, priority, due_date, created_at = task
            hours_remaining = (due_date - now).total_seconds() / 3600
            
            if hours_remaining <= 0:
                probability = 0.0
            else:
                X = np.array([[priority, hours_remaining]])
                X_scaled = scaler.transform(X)
                probability = model.predict(X_scaled)[0]
                probability = max(0.0, min(1.0, probability))
            
            priority_map = {1: "最高", 2: "高", 3: "中", 4: "低", 5: "最低"}
            due_date_str = due_date.strftime("%Y-%m-%d %H:%M")
            
            # 根据概率设置提醒级别
            if probability < 0.3:
                alert = "⚠️ 高风险：极可能逾期"
            elif probability < 0.6:
                alert = "⚠️ 中等风险：可能逾期"
            else:
                alert = "✅ 低风险：有望按时完成"
                
            print(f"ID: {task_id}")
            print(f"标题: {title}")
            print(f"优先级: {priority_map[priority]}")
            print(f"截止日期: {due_date_str}")
            print(f"完成概率: {probability:.1%} {alert}")
            print("-" * 60)
            
    except Error as err:
        print(f"查看预测概率时出错: {err}")


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
