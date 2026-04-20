---
name: improvement-orchestrator
description: Review this custom Odoo codebase and determine which single maintenance focus area would currently yield the highest value if improved now. Then, perform a deep implementation-oriented pass on that focus area until remaining improvements are marginal.
argument-hint: None
# tools: ['vscode', 'execute', 'read', 'agent', 'edit', 'search', 'web', 'todo'] # specify the tools this agent can use. If not set, all enabled tools are allowed.
---

<!-- Tip: Use /create-agent in chat to generate content with agent assistance -->

Review this custom Odoo codebase and determine which single maintenance focus area would currently yield the highest value if improved now.

Choose from:
- UX
- business logic correctness
- security and access rights
- performance and scalability
- maintainability and code health
- test coverage and regression prevention
- data model quality
- workflow and process fit
- search/reporting and decision support
- consistency and product coherence
- upgrade readiness and Odoo compatibility
- admin and configuration experience
- documentation and onboarding
- observability and supportability
- integration robustness

First:
1. assess the current codebase briefly across these dimensions
2. choose the highest-value focus area
3. justify the choice
4. then perform a deep implementation-oriented pass on that focus area
5. continue until remaining improvements are marginal