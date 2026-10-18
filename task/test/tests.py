from hstest import StageTest, TestedProgram, CheckResult, dynamic_test
import os
import json
from pathlib import Path


class PersonalAssistantTests(StageTest):
    """Blackbox tests for Personal Assistant using hstest."""

    @staticmethod
    def cleanup_tasks_db():
        """Clean up tasks.json file if it exists."""
        tasks_file = Path('tasks.json')
        if tasks_file.exists():
            tasks_file.unlink()

    # ==================== TasksStore Basic Tests ====================

    @dynamic_test(time_limit=100000)
    def test_create_task_basic(self):
        """Test basic task creation and verification."""
        self.cleanup_tasks_db()

        pr = TestedProgram()
        pr.start()

        # Create a task
        output = pr.execute('hey, create task "do laundry"')

        if "exception" in output.lower() or "error" in output.lower():
            pr.execute("/q")
            return CheckResult.wrong(f"Task creation failed: {output}")

        # Verify by finding the task
        output = pr.execute("what are tasks in todo?")

        if "do laundry" not in output.lower():
            pr.execute("/q")
            return CheckResult.wrong(f"Task 'do laundry' was not found in todo tasks. Output: {output}")

        pr.execute("/q")
        return CheckResult.correct()

    @dynamic_test(time_limit=100000)
    def test_create_and_find_task(self):
        """Test creating a task with specific status and finding it."""
        self.cleanup_tasks_db()

        pr = TestedProgram()
        pr.start()

        # Create a task with in_progress status
        pr.execute('create task "write code" with status in_progress')

        # Find the task by status
        output = pr.execute("what are tasks in progress?")

        if "write code" not in output.lower():
            pr.execute("/q")
            return CheckResult.wrong(f"Task 'write code' not found in in_progress tasks. Output: {output}")

        pr.execute("/q")
        return CheckResult.correct()

    @dynamic_test(time_limit=100000)
    def test_update_task_status(self):
        """Test updating task status and verifying the change."""
        self.cleanup_tasks_db()

        pr = TestedProgram()
        pr.start()

        # Create a task
        pr.execute('create task "deploy app"')

        # Verify it's in todo
        output = pr.execute("show me todo tasks")
        if "deploy app" not in output.lower():
            pr.execute("/q")
            return CheckResult.wrong(f"Task 'deploy app' not found in todo. Output: {output}")

        # Update to in_progress
        pr.execute("I started to deploy app")

        # Verify it's in in_progress
        output = pr.execute("what tasks are in progress?")
        if "deploy app" not in output.lower():
            pr.execute("/q")
            return CheckResult.wrong(f"Task 'deploy app' not found in in_progress after update. Output: {output}")

        # Verify it's NOT in todo anymore
        output = pr.execute("show me todo tasks")
        if "deploy app" in output.lower() and "no task" not in output.lower():
            pr.execute("/q")
            return CheckResult.wrong(f"Task 'deploy app' still in todo after moving to in_progress. Output: {output}")

        pr.execute("/q")
        return CheckResult.correct()

    @dynamic_test(time_limit=100000)
    def test_create_multiple_tasks(self):
        """Test creating multiple tasks and finding them."""
        self.cleanup_tasks_db()

        pr = TestedProgram()
        pr.start()

        # Create multiple tasks
        pr.execute('create task "task one" with status todo')
        pr.execute('create task "task two" with status in_progress')
        pr.execute('create task "task three" with status done')

        # Verify todo task
        output = pr.execute("what is in my todo tasks?")
        if "task one" not in output.lower():
            pr.execute("/q")
            return CheckResult.wrong(f"Task 'task one' not found in todo. Output: {output}")

        # Verify in_progress task
        output = pr.execute("what is in my in_progress tasks?")
        if "task two" not in output.lower():
            pr.execute("/q")
            return CheckResult.wrong(f"Task 'task two' not found in in_progress. Output: {output}")

        # Verify done task
        output = pr.execute("what are done tasks?")
        if "task three" not in output.lower():
            pr.execute("/q")
            return CheckResult.wrong(f"Task 'task three' not found in done. Output: {output}")

        pr.execute("/q")
        return CheckResult.correct()

    @dynamic_test(time_limit=100000)
    def test_update_nonexistent_task(self):
        """Test updating a task that doesn't exist."""
        self.cleanup_tasks_db()

        pr = TestedProgram()
        pr.start()

        # Create one task
        pr.execute('create task "existing task"')

        # Try to update non-existent task
        output = pr.execute("mark task 'nonexistent' as done")

        # Should not crash
        if not pr.is_waiting_input():
            return CheckResult.wrong(f"Program crashed when updating nonexistent task: {output}")

        pr.execute("/q")
        return CheckResult.correct()

    @dynamic_test(time_limit=100000)
    def test_find_nonexistent_task(self):
        """Test finding a task that doesn't exist."""
        self.cleanup_tasks_db()

        pr = TestedProgram()
        pr.start()

        # Create one task
        pr.execute('create task "real task"')

        # Try to find non-existent task
        output = pr.execute("show me task 'fake task'")

        # Should indicate no results
        if "exception" in output.lower():
            pr.execute("/q")
            return CheckResult.wrong(f"Program crashed when finding nonexistent task: {output}")

        pr.execute("/q")
        return CheckResult.correct()

    # ==================== Context and Conversation Tests ====================

    @dynamic_test(time_limit=100000)
    def test_conversation_flow(self):
        """Test that conversation maintains context through multiple turns."""
        self.cleanup_tasks_db()

        pr = TestedProgram()
        pr.start()

        # Multi-turn conversation
        pr.execute('create task "learn python"')
        pr.execute('create task "build project" with status in_progress')

        # Ask about tasks
        output = pr.execute("what tasks do I have in todo?")
        if "learn python" not in output.lower():
            pr.execute("/q")
            return CheckResult.wrong(f"Context not maintained. Expected 'learn python' in output: {output}")

        output = pr.execute("and what about in progress?")
        if "build project" not in output.lower():
            pr.execute("/q")
            return CheckResult.wrong(f"Context not maintained. Expected 'build project' in output: {output}")

        pr.execute("/q")
        return CheckResult.correct()

    @dynamic_test(time_limit=100000)
    def test_empty_input_handling(self):
        """Test that empty input is handled gracefully."""
        self.cleanup_tasks_db()

        pr = TestedProgram()
        pr.start()

        # Send empty inputs
        pr.execute("")
        pr.execute("")

        # Should still be running
        if not pr.is_waiting_input():
            return CheckResult.wrong("Program should continue running after empty input")

        # Should still accept valid commands
        pr.execute('create task "test"')
        output = pr.execute("show me todo tasks")

        if "test" not in output.lower():
            pr.execute("/q")
            return CheckResult.wrong(f"Program not functioning correctly after empty inputs. Output: {output}")

        pr.execute("/q")
        return CheckResult.correct()

    # ==================== Tool Calling Tests ====================

    @dynamic_test(time_limit=100000)
    def test_tool_selection_create(self):
        """Test that LLM correctly selects create_task tool."""
        self.cleanup_tasks_db()

        pr = TestedProgram()
        pr.start()

        # Natural language request
        pr.execute("I need to add a new task called 'finish report' that's in progress")

        # Verify task was created by finding it
        output = pr.execute("show me tasks in progress")

        if "finish report" not in output.lower():
            pr.execute("/q")
            return CheckResult.wrong(f"LLM did not correctly create task. Output: {output}")

        pr.execute("/q")
        return CheckResult.correct()

    @dynamic_test(time_limit=100000)
    def test_tool_selection_find(self):
        """Test that LLM correctly selects find_task tool."""
        self.cleanup_tasks_db()

        pr = TestedProgram()
        pr.start()

        # Create a task first
        pr.execute('create task "read book" with status todo')

        # Natural language request to find
        output = pr.execute("can you look up my todo tasks?")

        if "read book" not in output.lower():
            pr.execute("/q")
            return CheckResult.wrong(f"LLM did not correctly find task. Output: {output}")

        pr.execute("/q")
        return CheckResult.correct()

    @dynamic_test(time_limit=100000)
    def test_tool_selection_update(self):
        """Test that LLM correctly selects update_task_status tool."""
        self.cleanup_tasks_db()

        pr = TestedProgram()
        pr.start()

        # Create a task
        pr.execute('create task "exercise"')

        # Natural language request to update
        pr.execute("mark the exercise task as done")

        # Verify update worked
        output = pr.execute("show me done tasks")

        if "exercise" not in output.lower():
            pr.execute("/q")
            return CheckResult.wrong(f"LLM did not correctly update task. Output: {output}")

        pr.execute("/q")
        return CheckResult.correct()

    @dynamic_test(time_limit=100000)
    def test_status_transitions(self):
        """Test updating task through different status transitions."""
        self.cleanup_tasks_db()

        pr = TestedProgram()
        pr.start()

        # Create task (defaults to todo)
        pr.execute('create task "important work"')

        # Move to in_progress
        pr.execute("I started working on important work")
        output = pr.execute("what's in progress?")
        if "important work" not in output.lower():
            pr.execute("/q")
            return CheckResult.wrong(f"Task not moved to in_progress. Output: {output}")

        # Move to done
        pr.execute("I finished important work")
        output = pr.execute("what's done?")
        if "important work" not in output.lower():
            pr.execute("/q")
            return CheckResult.wrong(f"Task not moved to done. Output: {output}")

        pr.execute("/q")
        return CheckResult.correct()

    # ==================== Data Persistence Tests ====================

    @dynamic_test(time_limit=100000)
    def test_data_persists_between_runs(self):
        """Test that tasks persist after program restart."""
        self.cleanup_tasks_db()

        # First run - create tasks
        pr1 = TestedProgram()
        pr1.start()
        pr1.execute('create task "persistent task" with status todo')
        pr1.execute('create task "another persistent" with status done')
        pr1.execute("/q")

        # Second run - find tasks
        pr2 = TestedProgram()
        pr2.start()

        output = pr2.execute("show me todo tasks")
        if "persistent task" not in output.lower():
            pr2.execute("/q")
            return CheckResult.wrong(f"Todo task did not persist. Output: {output}")

        output = pr2.execute("show me done tasks")
        if "another persistent" not in output.lower():
            pr2.execute("/q")
            return CheckResult.wrong(f"Done task did not persist. Output: {output}")

        pr2.execute("/q")
        return CheckResult.correct()

if __name__ == '__main__':
    PersonalAssistantTests().run_tests()