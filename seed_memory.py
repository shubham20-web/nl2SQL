"""
seed_memory.py
Pre-seeds Vanna 2.0 DemoAgentMemory with 15 question->SQL pairs.
Run: python seed_memory.py
"""

import asyncio
import uuid

from vanna_setup import get_agent
from vanna.capabilities.agent_memory import ToolMemory
from vanna.core.tool import ToolContext
from vanna.core.user.models import User

TRAINING_EXAMPLES = [
    ToolMemory(question="How many patients do we have?", tool_name="run_sql",
        args={"sql": "SELECT COUNT(*) AS total_patients FROM patients"}),
    ToolMemory(question="List all patients from Mumbai", tool_name="run_sql",
        args={"sql": "SELECT first_name, last_name, email, phone FROM patients WHERE city = 'Mumbai'"}),
    ToolMemory(question="How many male and female patients do we have?", tool_name="run_sql",
        args={"sql": "SELECT gender, COUNT(*) AS count FROM patients GROUP BY gender"}),
    ToolMemory(question="Which city has the most patients?", tool_name="run_sql",
        args={"sql": "SELECT city, COUNT(*) AS patient_count FROM patients GROUP BY city ORDER BY patient_count DESC LIMIT 1"}),
    ToolMemory(question="List all doctors and their specializations", tool_name="run_sql",
        args={"sql": "SELECT name, specialization, department FROM doctors ORDER BY specialization"}),
    ToolMemory(question="Which doctor has the most appointments?", tool_name="run_sql",
        args={"sql": "SELECT d.name, COUNT(a.id) AS appointment_count FROM doctors d JOIN appointments a ON a.doctor_id = d.id GROUP BY d.name ORDER BY appointment_count DESC LIMIT 1"}),
    ToolMemory(question="How many appointments does each doctor have?", tool_name="run_sql",
        args={"sql": "SELECT d.name, d.specialization, COUNT(a.id) AS total FROM doctors d LEFT JOIN appointments a ON a.doctor_id=d.id GROUP BY d.id ORDER BY total DESC"}),
    ToolMemory(question="How many appointments are there by status?", tool_name="run_sql",
        args={"sql": "SELECT status, COUNT(*) AS count FROM appointments GROUP BY status ORDER BY count DESC"}),
    ToolMemory(question="Show appointments from the last 30 days", tool_name="run_sql",
        args={"sql": "SELECT a.id, p.first_name, p.last_name, d.name AS doctor, a.appointment_date, a.status FROM appointments a JOIN patients p ON p.id=a.patient_id JOIN doctors d ON d.id=a.doctor_id WHERE a.appointment_date >= DATE('now','-30 days') ORDER BY a.appointment_date DESC"}),
    ToolMemory(question="How many cancelled appointments were there last quarter?", tool_name="run_sql",
        args={"sql": "SELECT COUNT(*) AS cancelled_count FROM appointments WHERE status='Cancelled' AND appointment_date >= DATE('now','-3 months')"}),
    ToolMemory(question="What is the total revenue?", tool_name="run_sql",
        args={"sql": "SELECT SUM(total_amount) AS total_revenue FROM invoices WHERE status='Paid'"}),
    ToolMemory(question="Show revenue by doctor", tool_name="run_sql",
        args={"sql": "SELECT d.name, SUM(i.total_amount) AS total_revenue FROM invoices i JOIN appointments a ON a.patient_id=i.patient_id JOIN doctors d ON d.id=a.doctor_id GROUP BY d.name ORDER BY total_revenue DESC"}),
    ToolMemory(question="List all unpaid invoices", tool_name="run_sql",
        args={"sql": "SELECT p.first_name, p.last_name, i.invoice_date, i.total_amount, i.paid_amount, i.status FROM invoices i JOIN patients p ON p.id=i.patient_id WHERE i.status IN ('Pending','Overdue') ORDER BY i.invoice_date DESC"}),
    ToolMemory(question="Top 5 patients by total spending", tool_name="run_sql",
        args={"sql": "SELECT p.first_name, p.last_name, SUM(i.total_amount) AS total_spending FROM invoices i JOIN patients p ON p.id=i.patient_id GROUP BY p.id ORDER BY total_spending DESC LIMIT 5"}),
    ToolMemory(question="Show monthly appointment count for the past 6 months", tool_name="run_sql",
        args={"sql": "SELECT STRFTIME('%Y-%m', appointment_date) AS month, COUNT(*) AS count FROM appointments WHERE appointment_date >= DATE('now','-6 months') GROUP BY month ORDER BY month"}),
]


async def seed():
    agent  = get_agent()
    memory = agent.agent_memory
    user   = User(id="admin", email="admin@clinic.com", group_memberships=["admin","user"])

    print(f"Seeding {len(TRAINING_EXAMPLES)} Q&A pairs...\n")
    passed = 0
    for i, ex in enumerate(TRAINING_EXAMPLES, 1):
        ctx = ToolContext(
            user=user,
            conversation_id=str(uuid.uuid4()),
            request_id=str(uuid.uuid4()),
            agent_memory=memory,
        )
        try:
            await memory.save_tool_usage(
                question=ex.question, tool_name=ex.tool_name,
                args=ex.args, context=ctx, success=True,
            )
            print(f"  [{i:02d}] ✅ {ex.question[:65]}")
            passed += 1
        except Exception as e:
            print(f"  [{i:02d}] ❌ {e}")

    print(f"\n✅ Done: {passed}/{len(TRAINING_EXAMPLES)} pairs saved.")


if __name__ == "__main__":
    asyncio.run(seed())
