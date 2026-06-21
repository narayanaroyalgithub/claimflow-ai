"""Domain services backing each agent and FastAPI endpoint.

Split by domain (patient, timeline, utilization, procedure, medication,
summary) so each module stays focused, rather than one large
``services.py`` God file.
"""
