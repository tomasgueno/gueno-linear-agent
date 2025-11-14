import anthropic
import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# URLs y configuración
LINEAR_API_URL = "https://api.linear.app/graphql"

def get_headers():
    """Obtiene headers para Linear API"""
    return {
        "Authorization": os.environ.get("LINEAR_API_KEY"),
        "Content-Type": "application/json"
    }

def execute_linear_graphql(query, variables=None):
    """Ejecuta una query GraphQL contra Linear"""
    headers = get_headers()
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    response = requests.post(
        LINEAR_API_URL,
        json=payload,
        headers=headers
    )
    
    if response.status_code != 200:
        raise Exception(f"Linear API error: {response.status_code} - {response.text}")
    
    return response.json()

def execute_linear_tool(tool_name, tool_input):
    """
    Ejecuta un tool call específico de Linear.
    Mapea el tool name a la query GraphQL correspondiente.
    """
    
    print(f"  → Executing {tool_name} with input: {json.dumps(tool_input, indent=2)}")
    
    # LINEAR: LIST ISSUES
    if tool_name == "linear_list_issues":
        query = """
        query($first: Int, $filter: IssueFilter) {
          issues(first: $first, filter: $filter) {
            nodes {
              id
              identifier
              title
              description
              url
              createdAt
              updatedAt
              dueDate
              priority
              state {
                name
                type
              }
              assignee {
                id
                name
                email
              }
              project {
                id
                name
              }
              team {
                id
                name
              }
              labels {
                nodes {
                  id
                  name
                }
              }
            }
          }
        }
        """
        
        # Construir filtros
        filters = {}
        
        if tool_input.get("project"):
            filters["project"] = {"name": {"eq": tool_input["project"]}}
        
        if tool_input.get("team"):
            filters["team"] = {"name": {"eq": tool_input["team"]}}
        
        if tool_input.get("assignee"):
            filters["assignee"] = {"name": {"eq": tool_input["assignee"]}}
        
        if tool_input.get("state"):
            filters["state"] = {"name": {"eq": tool_input["state"]}}
        
        variables = {
            "first": tool_input.get("limit", 50),
            "filter": filters if filters else None
        }
        
        result = execute_linear_graphql(query, variables)
        return result.get("data", {}).get("issues", {}).get("nodes", [])
    
    # LINEAR: GET ISSUE
    elif tool_name == "linear_get_issue":
        query = """
        query($id: String!) {
          issue(id: $id) {
            id
            identifier
            title
            description
            url
            createdAt
            updatedAt
            dueDate
            priority
            state {
              name
              type
            }
            assignee {
              id
              name
              email
            }
            project {
              id
              name
            }
            team {
              id
              name
            }
            labels {
              nodes {
                id
                name
              }
            }
            comments {
              nodes {
                id
                body
                createdAt
                user {
                  name
                }
              }
            }
          }
        }
        """
        
        variables = {"id": tool_input["id"]}
        result = execute_linear_graphql(query, variables)
        return result.get("data", {}).get("issue", {})
    
    # LINEAR: CREATE COMMENT
    elif tool_name == "linear_create_comment":
        mutation = """
        mutation($issueId: String!, $body: String!) {
          commentCreate(input: {
            issueId: $issueId
            body: $body
          }) {
            success
            comment {
              id
              body
              createdAt
            }
          }
        }
        """
        
        variables = {
            "issueId": tool_input["issueId"],
            "body": tool_input["body"]
        }
        
        result = execute_linear_graphql(mutation, variables)
        return result.get("data", {}).get("commentCreate", {})
    
    else:
        raise Exception(f"Unknown tool: {tool_name}")

def run_quality_check():
    """Ejecuta el chequeo de calidad completo"""
    
    print(f"\n{'='*60}")
    print(f"🤖 GUENO LINEAR QUALITY AGENT")
    print(f"Started at: {datetime.now()}")
    print(f"{'='*60}\n")
    
    # Inicializar Claude client
    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )
    
    # System prompt completo
    system_prompt = """
# Claude System Prompt — Gueno: Linear Weekly TODOs Quality Agent

## ROLE

You are the **Gueno Linear Quality Agent**, responsible for validating, monitoring, and enforcing the operational quality of all tasks inside the **Weekly TODOs** project in Linear.

Your mission: maintain clarity, accountability, and a consistent execution rhythm.

You must operate according to Gueno's principles:

* **Linear = source of truth**
* **Slack = fast communication, never tasks**
* **Everything said → written → executed → reviewed**
* **Nothing is said twice**
* **Short > Long**
* **Done > Promised**
* **Public > Private**

---

## CRITICAL: COMMUNICATION STYLE

Every comment you post must be:
- **Maximum 8 lines**
- **No greetings or pleasantries**
- **No explanations of your process** ("I analyzed", "I noticed")
- **Bullets only, no prose**
- **Actions first, context second**
- **Remove every unnecessary word**

---

## 1. Automatic Validation of Every New Task

Classify each new task as **Clear** or **Not clear**.

### A task is Clear ONLY if it has:

1. **Short, actionable title** (specific action + outcome)
2. **Explicit deliverable** (link, file, message, or verifiable output)
3. **One assigned owner**
4. **Defined deadline** (typically within **48h** for Weekly TODOs)
5. **Sufficient context** to execute without asking questions

### If anything is missing:

Post a comment listing problems + suggestions using the formats in Section 5.

---

## 2. Continuous Monitoring — 48h Activity Rule

Every task must show activity at least every **48 hours**.

If a task goes 48h without changes:
```
48h without update

Last activity: [date]

Update needed: status, blockers, or new ETA
```

---

## 3. Overdue Task Detection

If a task reaches its deadline and is not completed:
```
Overdue since [date]

Action: Complete now or re-estimate or document blocker or close.
```

---

## 4. Mandatory Gueno Operational Rules

Strictly enforce:

* No task without **owner**
* No task without **deadline**
* No task without **explicit deliverable**
* No vague tasks (e.g., "review", "think", "chat")
* Strategic tasks must link to a **doc or KR**
* Tasks created from decisions must reference the **#decisions** Slack message

---

## 5. Comment Examples — By Issue Type

**Core rule:** Minimum words. No explanations, only facts + actions.

---

### Issue Type 1: No Deadline
```
To fix:
- No deadline
```

---

### Issue Type 2: No Owner
```
To fix:
- No owner
```

---

### Issue Type 3: Vague Task Title
```
To fix:
- Vague task title

Suggestion:
Title: "Review Q4 roadmap doc and comment on priorities"
```

---

### Issue Type 4: Empty Description
```
To fix:
- Empty description
```

---

### Issue Type 5: No Clear Deliverable
```
To fix:
- No clear deliverable

Specify output: Doc link? Message? PR?
```

---

### Issue Type 6: Task Done, No Deliverable Visible
```
Task marked Done but no deliverable visible.

Add link to output or reopen.
```

---

### Issue Type 7: Task Overdue
```
Overdue since [date]

Action: Complete now or re-estimate or document blocker or close.
```

---

### Multi-Issue Example (Most Common)
```
To fix:
- No deadline
- No deliverable
- Vague task
- Empty description

Suggestions:
1. Title: "Review Q4 roadmap doc and add priority comments"
2. Description: "Comment on priorities by EOD"
3. Deliverable: Link to commented doc
```

---

## AGENT TL;DR

* Validate clarity → comment
* Monitor 48h activity → comment
* Check deadlines → comment
* Enforce Gueno's execution culture
* Keep tasks actionable, updated, owned, and concise
* Never assume, never invent
* Always be **short, precise, operational**
"""
    
    # Definir Linear tools
    linear_tools = [
        {
            "name": "linear_list_issues",
            "description": "List issues in the user's Linear workspace",
            "input_schema": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "The project name or ID to filter by"
                    },
                    "team": {
                        "type": "string",
                        "description": "The team name or ID to filter by"
                    },
                    "assignee": {
                        "type": "string",
                        "description": "The assignee to filter by"
                    },
                    "state": {
                        "type": "string",
                        "description": "The state name or ID to filter by"
                    },
                    "limit": {
                        "type": "number",
                        "description": "The number of results to return (Max is 250)",
                        "default": 50
                    },
                    "includeArchived": {
                        "type": "boolean",
                        "description": "Whether to include archived issues",
                        "default": False
                    }
                }
            }
        },
        {
            "name": "linear_get_issue",
            "description": "Retrieve detailed information about an issue by ID",
            "input_schema": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The issue ID"
                    }
                },
                "required": ["id"]
            }
        },
        {
            "name": "linear_create_comment",
            "description": "Create a comment on a specific Linear issue",
            "input_schema": {
                "type": "object",
                "properties": {
                    "issueId": {
                        "type": "string",
                        "description": "The issue ID"
                    },
                    "body": {
                        "type": "string",
                        "description": "The content of the comment as Markdown"
                    }
                },
                "required": ["issueId", "body"]
            }
        }
    ]
    
    # Iniciar conversación
    messages = [
        {
            "role": "user",
            "content": "Run complete quality check on Weekly TODOs project. Scan all tasks and post comments where needed."
        }
    ]
    
    # Loop principal de ejecución
    iteration = 0
    max_iterations = 50  # Límite de seguridad
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")
        
        # Llamar a Claude
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            system=system_prompt,
            tools=linear_tools,
            messages=messages
        )
        
        print(f"Stop reason: {response.stop_reason}")
        
        # Si Claude terminó (no más tool calls)
        if response.stop_reason == "end_turn":
            print("\n✅ Quality check completed!")
            
            # Imprimir respuesta final
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\n{block.text}")
            
            break
        
        # Si Claude quiere usar tools
        if response.stop_reason == "tool_use":
            # Agregar respuesta de Claude al historial
            messages.append({
                "role": "assistant",
                "content": response.content
            })
            
            # Ejecutar cada tool call
            tool_results = []
            
            for content_block in response.content:
                if content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_input = content_block.input
                    
                    try:
                        # Ejecutar el tool
                        result = execute_linear_tool(tool_name, tool_input)
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": json.dumps(result)
                        })
                        
                        print(f"  ✅ {tool_name} executed successfully")
                        
                    except Exception as e:
                        print(f"  ❌ Error executing {tool_name}: {str(e)}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": f"Error: {str(e)}",
                            "is_error": True
                        })
            
            # Agregar resultados al historial
            messages.append({
                "role": "user",
                "content": tool_results
            })
        
        else:
            print(f"Unexpected stop reason: {response.stop_reason}")
            break
    
    if iteration >= max_iterations:
        print("\n⚠️ Reached max iterations limit")
    
    print(f"\n{'='*60}")
    print(f"Finished at: {datetime.now()}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    try:
        run_quality_check()
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        raise
