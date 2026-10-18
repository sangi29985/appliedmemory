from openai import OpenAI
import os
import re
import dotenv
from tinydb import TinyDB, Query
from enum import Enum

dotenv.load_dotenv()

CLIENT = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY")
)

class ContextManager:
    def __init__(self):
        self.messages: list[dict] = []
        
    def add_user_message(self, message: str):
        self.messages.append({
            "role": "user", "content": message
        })
    
    def update_messages(self, messages: list[dict]):
        self.messages = messages
        
    def get_repr(self):
        """Function for showing context for easier solving of optional tasks"""
        msgs = []
        for elem in self.messages:
            if type(elem) is dict:
                if 'role' in elem:
                    msgs.append(elem['role'] + ': ' + elem['content'][:15] + '...')
                else:
                    msgs.append(elem['type'] + ': ' + elem['output'][:15] + '...')
            else:
                msgs.append(str(elem.type))
        return 'Context:\n\t' + "\n\t".join(msgs) + '\n-------'
    
    def get_context(self) -> list[dict]:
        return self.messages.copy()

    def compact(self):
        """
        OPTIONAL TASK
        
        If you use get_repr() function after each call to LLM, 
        you will see that context is getting bigger and bigger. Not only with messages, but also with function calls and their outputs. 
        
        Your task is to implement compact() function to remove all non-message items from context.
        """
        compacted = []
        for elem in self.messages:
            if type(elem) is dict:
                if "role" in elem:
                    compacted.append(elem)
            elif getattr(elem, "type", None) == "message":
                compacted.append(elem)
        self.messages = compacted
    
    def reset(self):
        self.messages = []
        
class MatchType(Enum):
    EQ = "eq"
    CONTAINS = "contains"


VALID_STATUSES = ("to-do", "in-progress", "done")


def _normalize_status(status: str) -> str:
    """Map user and model phrasing onto the three stored statuses."""
    if status is None or str(status).strip() == "":
        return "to-do"
    cleaned = re.sub(r"[\s_]+", "-", str(status).strip().lower())
    aliases = {
        "todo": "to-do",
        "to-do": "to-do",
        "in-progress": "in-progress",
        "inprogress": "in-progress",
        "doing": "in-progress",
        "started": "in-progress",
        "done": "done",
        "complete": "done",
        "completed": "done",
        "finished": "done",
    }
    return aliases.get(cleaned, str(status).strip())


def _clean_text(value: str) -> str:
    return str(value).strip().strip('"').strip("'").strip()
    
  
class TasksStore:
    def __init__(self):
        self.db = TinyDB('tasks.json')
        
    def create_task(self, name: str, status: str = "to-do") -> str:
        """
        TODO: implement task creation
        
        Returns:
            str: Task creation message
        """
        name = _clean_text(name)
        status = _normalize_status(status)
        self.db.insert({"name": name, "status": status})
        return f'The task "{name}" has been created and is marked as {status}.'
        
    def find_task(self, key: str, value: str, match: MatchType = MatchType.EQ) -> str:
        """
        TODO: implement task search by field value or by field value pattern.
        
        Tip 1: use tinydb search functionality. 
        Also, use regex for pattern matching (MatchType.Contains).

        Tip 2: remember to select match by value, not by name.
        i.e.
        -> match == MatchType.EQ is not correct
        -> match == MatchType.EQ.value is correct
        
        Returns:
            str: Task search result
        """
        if isinstance(match, MatchType):
            match = match.value
        else:
            match = str(match).strip().lower()

        search_value = _clean_text(value)
        if key == "status":
            search_value = _normalize_status(search_value)

        query = Query()
        field = query[key]
        if match == MatchType.CONTAINS.value and search_value not in VALID_STATUSES:
            results = self.db.search(
                field.search(re.escape(search_value), flags=re.IGNORECASE)
            )
        else:
            results = self.db.search(field == search_value)
            if not results and key == "name":
                results = self.db.search(
                    field.matches(f"(?i)^{re.escape(search_value)}$")
                )

        if not results:
            return f'No tasks found where {key} is "{value}".'

        details = [
            f'"{task["name"]}" (status: {task["status"]})' for task in results
        ]
        noun = "task" if len(details) == 1 else "tasks"
        return f"Found {len(details)} {noun}: " + "; ".join(details) + "."
        
    def update_task_status(self, name: str, new_status: str) -> str:
        """
        TODO: implement task status update

        Tip: use self.db.update(...) with 2 params: field and query.
        Field - field to update
        Query - ability to select portion of data to update
        
        Returns:
            str: Task status update message
        """
        name = _clean_text(name)
        new_status = _normalize_status(new_status)
        query = Query()
        updated = self.db.update({"status": new_status}, query.name == name)
        if not updated:
            updated = self.db.update(
                {"status": new_status},
                query.name.matches(f"(?i)^{re.escape(name)}$"),
            )
        if not updated:
            return f'No task named "{name}" was found.'
        return f'The task "{name}" is now marked as {new_status}.'
  
    def flush(self):
        """
        TODO: clear database 
        """
        self.db.truncate()
    
    
class PersonalAssistant:
    def __init__(self):
        """
        TODO: fill tools list with correct tool descriptions. Match tool names to function names. And tool parameters to function parameters.
        
        As a hint, check how tool_result is obtained during tool call phase.
        """
        self.tools = [
            {
                "type": "function",
                "name": "find_task",
                "description": (
                    "Search stored tasks. Use this whenever the user asks which tasks exist, "
                    "asks to list tasks, or asks about a status or a name. "
                    "For status lookups set key to 'status' and value to exactly one of "
                    "'to-do', 'in-progress', or 'done'. "
                    "Map todo/to do to 'to-do', in progress/in_progress to 'in-progress', "
                    "and done/finished/completed to 'done'. "
                    "For a task name set key to 'name'. Use match 'eq' for status and exact names, "
                    "and match 'contains' for a partial name."
                ),
                "strict": False,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "enum": ["name", "status"],
                            "description": "Field to search. 'status' lists tasks by status. 'name' looks up a task name.",
                        },
                        "value": {
                            "type": "string",
                            "description": "Value to match. For status use exactly 'to-do', 'in-progress', or 'done'.",
                        },
                        "match": {
                            "type": "string",
                            "enum": ["eq", "contains"],
                            "description": "Comparison. 'eq' is exact. 'contains' is a case-insensitive substring match. Defaults to 'eq'.",
                        },
                    },
                    "required": ["key", "value"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "create_task",
                "description": (
                    "Create and store a new task. Use this when the user wants to add, create, "
                    "or remember a task. If no status is given, use 'to-do'. "
                    "Valid statuses are exactly 'to-do', 'in-progress', and 'done'. "
                    "Map todo/to do to 'to-do', in progress/in_progress to 'in-progress', "
                    "and done/finished/completed to 'done'."
                ),
                "strict": False,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Task name exactly as the user stated it, without surrounding quotes.",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["to-do", "in-progress", "done"],
                            "description": "Task status. Use 'to-do' when the user does not specify one.",
                        },
                    },
                    "required": ["name", "status"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "update_task_status",
                "description": (
                    "Change the status of an existing task by its name. Use this when the user "
                    "starts, finishes, completes, or moves a task. "
                    "Valid statuses are exactly 'to-do', 'in-progress', and 'done'. "
                    "If the user started a task, set new_status to 'in-progress'. "
                    "If the user finished or completed it, set new_status to 'done'."
                ),
                "strict": False,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Exact name of the task to update.",
                        },
                        "new_status": {
                            "type": "string",
                            "enum": ["to-do", "in-progress", "done"],
                            "description": "New status: 'to-do', 'in-progress', or 'done'.",
                        },
                    },
                    "required": ["name", "new_status"],
                    "additionalProperties": False,
                },
            },
        ]
        # to store data
        self.tasks_store = TasksStore()
        
        self.tool_map = {
            "find_task": self.tasks_store.find_task,
            "create_task": self.tasks_store.create_task,
            "update_task_status": self.tasks_store.update_task_status
        }
        # to manage context
        self.context_manager = ContextManager()
        
    def send_message(self, message: str) -> str:
        self.context_manager.add_user_message(message)
        context = self.context_manager.get_context()
        context = self._call_llm(context)
        self.context_manager.update_messages(context)
        return context[-1].content[0].text
    
    def _call_llm(self, messages: list[dict]) -> list[dict]:
        response = CLIENT.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are a personal task assistant. Create, find, and update tasks only "
                        "through the provided tools. Never claim a task was stored, changed, or "
                        "listed unless a tool result says so. "
                        "Valid statuses are exactly to-do, in-progress, and done. "
                        "If the user does not specify a status, use to-do. "
                        "Map todo or to do to to-do, in progress or in_progress to in-progress, "
                        "and done, finished, or completed to done. "
                        "When the user asks what tasks they have, call find_task before answering. "
                        "Reply briefly and include every task name from the tool result."
                    ),
                }
            ] + messages,
            tools=self.tools
        )
        messages += response.output
        
        if not any(getattr(item, "type", None) == "function_call" for item in response.output):
            return messages

        # if not message, execute tool calls
        for item in response.output:
            if item.type == "function_call":
                try:
                    tool_result = self.tool_map[item.name](
                        **eval(item.arguments)
                    )
                except Exception:
                    tool_result = (
                        "The tool call could not be completed. "
                        "Check the argument names and values, then call the tool again."
                    )
                """
                TODO: Fill parameters of messages.append to make it work. messages.append requires tool result in special format. Check openai responses docs for more info
                """
                messages.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": str(tool_result),
                    }
                )
        """
        TODO: Change return value to make it work
        
        Something seems wrong here. 
        If we return the context messages right away, something will break. What can we do here, to continue the loop?
        """
        return self._call_llm(messages)
    
    def flush(self):
        self.tasks_store.flush()
        self.context_manager.reset()
        

def main():
    """Main conversation loop"""
    assistant = PersonalAssistant()
    while True:
        try:
            user_input = input("User: ").strip()
            if not user_input:
                continue
            
            # Process special commands
            if user_input == "/q":
                break
            elif user_input == "/flush":
                assistant.flush()
                print("[INFO] Flushed")
                continue
            
            # Process normal message
            response = assistant.send_message(user_input)
            print(f"Assistant: {response}")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
