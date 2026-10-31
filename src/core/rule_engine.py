import os
import json
import re
from datetime import timedelta, date
from typing import List, Dict, Any

class RuleEngine:
    """Evaluates role, department, and location rules to generate customized onboarding checklists."""

    @staticmethod
    def load_rules() -> List[Dict[str, Any]]:
        """Load onboarding checklist rules from data/rules/onboarding_requirements.json."""
        path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "rules", "onboarding_requirements.json")
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return []

    @staticmethod
    def load_owners() -> Dict[str, str]:
        """Load department owner email mappings."""
        path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "rules", "department_owners.json")
        try:
            with open(path, "r") as f:
                data = json.load(f)
                return {d["department"]: d["owner_email"] for d in data if "department" in d}
        except Exception:
            return {}

    @classmethod
    def generate_checklist_for_employee(cls, role: str, department: str, location: str, joining_date: date) -> List[Dict[str, Any]]:
        """Match rules and compute relative due dates and owner assignments."""
        rules = cls.load_rules()
        owners = cls.load_owners()
        tasks = []

        for rule in rules:
            # Check pattern matches for role, department and location
            role_match = bool(re.search(rule.get("role_pattern", ".*"), role, re.IGNORECASE))
            dept_match = bool(re.search(rule.get("department", ".*"), department, re.IGNORECASE))
            loc_match = bool(re.search(rule.get("location", ".*"), location, re.IGNORECASE))

            if role_match and dept_match and loc_match:
                offset = rule.get("relative_offset_days", 0)
                due_date = joining_date + timedelta(days=offset)
                dept = rule.get("assigned_department", "Human Resources")
                owner_email = owners.get(dept, "hr.ops@azentio.com")
                prereq = rule.get("prerequisite_task")

                # If prerequisite is required, mark as Blocked initially
                initial_status = "Blocked" if prereq else "Pending"

                tasks.append({
                    "task_code": rule["rule_code"],
                    "title": rule["task_title"],
                    "category": rule.get("category", "General"),
                    "assigned_department": dept,
                    "owner_email": owner_email,
                    "due_date": due_date,
                    "relative_offset_days": offset,
                    "status": initial_status,
                    "rule_origin": rule.get("rule_origin", "Standard organization policy"),
                    "prerequisite_task": prereq
                })

        return tasks

