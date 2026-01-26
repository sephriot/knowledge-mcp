# Knowledge-MCP Integration – Enforced Workflow (Tool-Agnostic)

You have access to a knowledge system that maintains persistent project knowledge. During all tasks, you MUST retrieve, apply, and update knowledge to improve task quality and reuse across future tasks. Knowledge usage is required but secondary to fulfilling the current objective.

==================== AVAILABLE CAPABILITIES ====================
Use your environment's knowledge tools to:
- search existing knowledge
- retrieve full entries
- create or update entries
- list, summarize, or manage entries

==================== REQUIRED WORKFLOW ====================

1) BEFORE PLANNING
- Extract domain keywords from the user request or context.
- Search for existing knowledge relevant to the task.
- Read full content for the most relevant results.
- If relevant knowledge exists, ground planning and decisions in it.

2) PLANNING & EXECUTION
- Use existing knowledge as guidance for decisions and implementation.
- Task completion remains the top priority. Knowledge use must not delay progress.
- When multiple entries apply, resolve conflicts based on:
  - confidence: high > medium > low
  - status: active > draft > deprecated
  - last updated: newer > older
- Re-search when:
  - a new subtask appears
  - you hit uncertainty or errors
  - you change target files or subsystems

3) CITE KNOWLEDGE
- At the end of the task response, include a Knowledge Used section.
- List each entry and how it influenced your decisions.

4) UPDATE KNOWLEDGE
- Only add knowledge that is reliable, reusable, and non-trivial.
- New entries must represent one clear concept.
- Create or update knowledge when you encounter:
  - confirmed best practices
  - recurring patterns
  - documented gotchas
  - definitions that help future reasoning
  - reusable code or procedures
- Provide sources for each new entry (e.g., code files, tickets, URLs, conversation).
- If unsure about accuracy or permanence, mark confidence as low.

5) FINALIZE
Conclude with the required sections:
- Knowledge used: One-line description of how each entry influenced your output.
- Knowledge changes: One-line description of any new or updated entries.

==================== GENERAL RULES ====================
- Retrieval before creation: Always look for applicable existing knowledge before inventing new content.
- Knowledge is supportive: Use it to improve task quality and future reuse, not to justify overengineering.
- Efficiency: Searching and retrieving knowledge must be efficient; avoid exhaustive exploration beyond relevant scope.
