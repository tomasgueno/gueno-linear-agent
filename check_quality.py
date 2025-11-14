import anthropic
import os
import requests
from datetime import datetime

LINEAR_API_URL = "https://api.linear.app/graphql"

def execute_linear_tool(tool_name, tool_input):
    """Ejecuta un tool call de Linear contra su API"""
    headers = {
        "Authorization": os.environ.get("LINEAR_API_KEY"),
        "Content-Type": "application/json"
    }
    
    if tool_name == "Linear_list_issues":
        query = """
        query($project: String!, $limit: Int) {
          issues(
            filter: { project: { name: { eq: $project } } }
            first: $limit
          ) {
            nodes {
              id
              identifier
              title
              description
              state { name }
              assignee { name }
              dueDate
              createdAt
              updatedAt
            }
          }
        }
        """
        response = requests.post(
            LINEAR_API_URL,
            json={"query": query, "variables": tool_input},
            headers=headers
        )
        return response.json()
    
    elif tool_name == "Linear_get_issue":
        query = """
        query($id: String!) {
          issue(id: $id) {
            id
            identifier
            title
            description
            state { name }
            assignee { name }
            dueDate
            createdAt
            updatedAt
          }
        }
        """
        response = requests.post(
            LINEAR_API_URL,
            json={"query": query, "variables": tool_input},
            headers=headers
        )
        return response.json()
    
    elif tool_name == "Linear_create_comment":
        mutation = """
        mutation($issueId: String!, $body: String!) {
          commentCreate(input: { issueId: $issueId, body: $body }) {
            success
            comment { id }
          }
        }
        """
        response = requests.post(
            LINEAR_API_URL,
            json={"query": mutation, "variables": tool_input},
            headers=headers
        )
        return response.json()

def run_quality_check():
    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )
    
    system_prompt = """[... el prompt completo ...]"""
    
    messages = [
        {
            "role": "user",
            "content": "Run complete quality check on Weekly TODOs project"
        }
    ]
    
    # Loop de ejecución de tools
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            system=system_prompt,
            tools=linear_tools,
            messages=messages
        )
        
        # Si Claude terminó (no más tool calls)
        if response.stop_reason != "tool_use":
            print(f"[{datetime.now()}] Check completed")
            print(response.content)
            break
        
        # Ejecutar cada tool call
        tool_results = []
        for content_block in response.content:
            if content_block.type == "tool_use":
                tool_name = content_block.name
                tool_input = content_block.input
                
                print(f"Executing {tool_name}...")
                result = execute_linear_tool(tool_name, tool_input)
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": str(result)
                })
        
        # Agregar resultados al historial
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

if __name__ == "__main__":
    run_quality_check()
