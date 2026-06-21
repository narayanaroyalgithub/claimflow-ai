"""LangGraph agent nodes.

Each module is a single agent in the workflow: it reads from the shared
``WorkflowState`` and returns a partial state update. Orchestration
(edges, ordering, compilation) stays in :mod:`app.workflow`.
"""
