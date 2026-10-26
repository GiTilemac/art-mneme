- Tasks are GitHub issues, one at a time
- Read the acceptance criteria before starting and before closing
- Commit regularly

Roles

- PM - creates a GitHub issue from a task in docs/tasks.md and grooms it before anyone implements it, follows docs/team/pm.md
- Dev - implements one groomed task, follows docs/team/dev.md
- QA - checks the result against the acceptance criteria, follows docs/team/qa-engineer.md
- Orchestrator - launches the PM, the dev and QA as subagents,  follows docs/team/orchestrator.md
- On-call engineer - investigates a firing alert and may commit a fix on its own branch for review, follows docs/team/on-call-engineer.md (started by `make on-call`)