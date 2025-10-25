import pytest
from datetime import datetime
from unittest.mock import MagicMock
import task  # 替换为你的主程序文件名（无.py）


# 自定义打印函数，增强可读性
def print_step(step, message):
    print(f"\n{'='*20} {step} {'='*20}")
    print(message)
    print(f"{'='*(42 + len(step))}\n")


@pytest.fixture
def fresh_mock_db():
    """每次调用都生成全新的模拟连接和游标"""
    def _create_mock():
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1,)  # PostgreSQL通过RETURNING返回ID
        mock_cursor.rowcount = 1  # 确保更新/删除返回成功
        return mock_conn, mock_cursor
    return _create_mock


def test_full_task_flow(fresh_mock_db, monkeypatch, capsys):
    """完整流程测试：添加→查看→更新→删除（带详细步骤输出）"""

    # ------------------------------
    # 1. 添加任务
    # ------------------------------
    print_step("步骤1: 添加任务", "开始执行任务添加测试...")
    mock_conn, mock_cursor = fresh_mock_db()

    # 模拟用户输入
    def add_input(prompt):
        response = {
            "请输入任务标题: ": "完整流程测试",
            "请输入任务描述 (可选): ": "这是一个测试任务",
            "请输入优先级 (1-最高, 2-高, 3-中, 4-低, 5-最低, 默认3): ": "2",
            "请输入截止日期 (格式: YYYY-MM-DD HH:MM, 可选): ": "2024-12-31 23:59"
        }.get(prompt, "")
        print(f"用户输入: {response}")  # 打印用户输入
        return response

    monkeypatch.setattr('builtins.input', add_input)

    # 执行添加
    task.add_task(mock_conn)

    # 获取输出并验证
    captured = capsys.readouterr()
    print(f"程序输出: {captured.out.strip()}")  # 打印程序输出

    # 验证结果
    assert "任务添加成功! 任务ID: 1" in captured.out, "添加任务验证失败"
    assert "INSERT INTO tasks" in mock_cursor.execute.call_args[0][0], "SQL语句不正确"
    assert "RETURNING id" in mock_cursor.execute.call_args[0][0], "缺少RETURNING子句"
    print_step("步骤1结果", "任务添加测试通过 ✅")

    # ------------------------------
    # 2. 查看任务
    # ------------------------------
    print_step("步骤2: 查看任务", "开始执行任务查询测试...")
    mock_conn, mock_cursor = fresh_mock_db()

    # 模拟数据库返回
    mock_cursor.fetchall.return_value = [
        (1, '完整流程测试', '这是一个测试任务', 2, False,
         datetime(2024, 12, 31, 23, 59), datetime(2024, 1, 1), None)
    ]
    print("模拟数据库返回数据: 1条测试任务")

    # 模拟用户选择
    def view_input(prompt):
        if "查询方式" in prompt:
            print("用户选择: 1 (查看所有任务)")
            return "1"
        return ""

    monkeypatch.setattr('builtins.input', view_input)

    # 执行查询
    task.view_tasks(mock_conn)

    # 验证结果
    captured = capsys.readouterr()
    print(f"程序输出片段: {captured.out[:100]}...")  # 打印部分输出

    assert "找到 1 个任务:" in captured.out, "未找到任务"
    assert "标题: 完整流程测试" in captured.out, "任务标题不正确"
    assert "优先级: 高" in captured.out, "优先级显示错误"
    assert "状态: ○ 未完成" in captured.out, "任务状态错误"
    print_step("步骤2结果", "任务查询测试通过 ✅")

    # ------------------------------
    # 3. 更新任务（标记完成）
    # ------------------------------
    print_step("步骤3: 更新任务", "开始执行任务更新测试...")
    mock_conn, mock_cursor = fresh_mock_db()

    # 模拟用户输入
    def update_input(prompt):
        if "任务ID" in prompt:
            print("用户输入ID: 1")
            return "1"
        elif "更新方式" in prompt:
            print("用户选择: 1 (标记为已完成)")
            return "1"
        return ""

    monkeypatch.setattr('builtins.input', update_input)

    # 执行更新
    task.update_task(mock_conn)

    # 验证结果
    captured = capsys.readouterr()
    print(f"程序输出: {captured.out.strip()}")

    assert "任务更新成功!" in captured.out, "更新任务失败"
    assert "is_completed = TRUE" in mock_cursor.execute.call_args[0][0], "更新状态错误"
    assert "CURRENT_TIMESTAMP" in mock_cursor.execute.call_args[0][0], "时间函数错误"
    print_step("步骤3结果", "任务更新测试通过 ✅")

    # ------------------------------
    # 4. 删除任务
    # ------------------------------
    print_step("步骤4: 删除任务", "开始执行任务删除测试...")
    mock_conn, mock_cursor = fresh_mock_db()

    # 模拟用户输入
    def delete_input(prompt):
        if "任务ID" in prompt:
            print("用户输入ID: 1")
            return "1"
        elif "确定要删除" in prompt:
            print("用户确认: y (确认删除)")
            return "y"
        return ""

    monkeypatch.setattr('builtins.input', delete_input)

    # 执行删除
    task.delete_task(mock_conn)

    # 验证结果
    captured = capsys.readouterr()
    print(f"程序输出: {captured.out.strip()}")

    assert "任务删除成功!" in captured.out, "删除任务失败"
    mock_cursor.execute.assert_called_once_with(
        "DELETE FROM tasks WHERE id = %s", ("1",)
    )
    print_step("步骤4结果", "任务删除测试通过 ✅")

    print("\n" + "="*50)
    print("🎉 所有测试步骤全部通过!")
    print("="*50 + "\n")


if __name__ == "__main__":
    pytest.main(["-s", __file__])  # 使用-s参数显示打印内容