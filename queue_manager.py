"""
queue_manager.py
----------------
Priority queue logic using Python's built-in heapq module.
Modules used: heapq, datetime

The heap stores tuples of:
    (priority_level, registered_at, patient_id, ticket_number)

Lower priority_level = higher urgency:
    EMERGENCY = 1  |  URGENT = 2  |  REGULAR = 3
"""

import heapq
import datetime
from database import get_queue, STATUS_OPEN


class HospitalQueue:
    """
    In-memory priority queue wrapper around heapq.
    Always re-syncs from the database so state is consistent
    even across Streamlit reruns.
    """

    def __init__(self):
        self._heap: list = []

    def load_from_db(self):
        """Rebuild the heap from the current database state."""
        self._heap = []
        waiting_patients = get_queue(status_filter=[STATUS_OPEN])
        for p in waiting_patients:
            entry = (
                p["priority_level"],
                p["registered_at"],
                p["id"],
                p["ticket_number"],
            )
            heapq.heappush(self._heap, entry)

    def peek(self) -> dict | None:
        """Return (without removing) the top-priority patient info."""
        if not self._heap:
            return None
        priority_level, registered_at, patient_id, ticket_number = self._heap[0]
        return {
            "priority_level": priority_level,
            "registered_at":  registered_at,
            "id":             patient_id,
            "ticket_number":  ticket_number,
        }

    def pop(self) -> dict | None:
        """Remove and return the top-priority patient info."""
        if not self._heap:
            return None
        priority_level, registered_at, patient_id, ticket_number = heapq.heappop(self._heap)
        return {
            "priority_level": priority_level,
            "registered_at":  registered_at,
            "id":             patient_id,
            "ticket_number":  ticket_number,
        }

    def size(self) -> int:
        return len(self._heap)

    def estimate_wait(self, patient_id: str, avg_service_min: float = 8.0) -> str:
        """
        Estimate wait time for a given patient based on their heap position.
        Assumes avg_service_min minutes per patient ahead of them.
        """
        position = 0
        for entry in self._heap:
            pid = entry[2]
            if pid == patient_id:
                break
            position += 1
        else:
            return "N/A"

        total_minutes = position * avg_service_min
        if total_minutes < 1:
            return "Next up!"
        elif total_minutes < 60:
            return f"~{int(total_minutes)} min"
        else:
            hours = int(total_minutes // 60)
            mins  = int(total_minutes % 60)
            return f"~{hours}h {mins}m"


def compute_wait_time_str(registered_at: str) -> str:
    """Return a human-readable elapsed time since registration."""
    reg  = datetime.datetime.fromisoformat(registered_at)
    now  = datetime.datetime.now()
    diff = now - reg
    total_seconds = int(diff.total_seconds())

    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        return f"{total_seconds // 60}m {total_seconds % 60}s"
    else:
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        return f"{h}h {m}m"