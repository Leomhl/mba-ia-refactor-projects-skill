"""Helper functions that are actually used.

The original file had 116 lines, six of whose functions were never called —
including `process_task_data`, 52 lines reimplementing a seventh version of
the validation. The constants defined here were not imported by anyone
either; they moved to `models/task.py` and `validators.py`, close to where
they are used.
"""


def format_date(date_obj):
    return str(date_obj) if date_obj else None


def calculate_percentage(part, total):
    if total == 0:
        return 0
    return round((part / total) * 100, 2)
