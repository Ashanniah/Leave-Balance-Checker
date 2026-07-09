"""Employee Leave Balance Checker CLI application."""

from __future__ import annotations

import argparse
import csv
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List

LOG_FORMAT = "%(levelname)s: %(message)s"
LOG_FILE = "employee_leave_checker.log"
LOW_LEAVE_THRESHOLD = 5
CRITICAL_LABEL = "CRITICAL"
WARNING_LABEL = "WARNING"
HEALTHY_LABEL = "HEALTHY"


@dataclass
class EmployeeRecord:
    """A single employee leave balance record."""

    name: str
    department: str
    leave_balance: float


def configure_logging() -> None:
    """Configure logging for the application."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Employee Leave Balance Checker",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--csv",
        default="employee.csv",
        help="Path to the employee leave balance CSV file",
    )
    return parser.parse_args()


def load_employee_records(csv_path: Path) -> List[EmployeeRecord]:
    """Load employee leave records from a CSV file."""
    logging.info("Loading employee records from %s", csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    records: List[EmployeeRecord] = []

    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError("CSV file is missing header row")

        required_columns = {"Employee", "Department", "LeaveBalance"}
        missing_columns = required_columns - set(reader.fieldnames)
        if missing_columns:
            raise ValueError(
                f"CSV is missing required columns: {', '.join(sorted(missing_columns))}"
            )

        for row in reader:
            name = row.get("Employee", "").strip()
            department = row.get("Department", "").strip()
            balance_text = row.get("LeaveBalance", "").strip()

            if not name:
                logging.warning("Skipping row with missing employee name: %s", row)
                continue

            try:
                leave_balance = float(balance_text)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid leave balance for {name}: {balance_text}"
                ) from exc

            records.append(
                EmployeeRecord(name=name, department=department, leave_balance=leave_balance)
            )

    return records


def classify_record(record: EmployeeRecord) -> str:
    """Classify an employee record by leave balance severity."""
    if record.leave_balance < 0:
        return CRITICAL_LABEL
    if record.leave_balance < LOW_LEAVE_THRESHOLD:
        return WARNING_LABEL
    return HEALTHY_LABEL


def build_summary(records: List[EmployeeRecord]) -> Dict[str, object]:
    """Build a summary of employee leave balances."""
    groups: Dict[str, List[EmployeeRecord]] = {
        CRITICAL_LABEL: [],
        WARNING_LABEL: [],
        HEALTHY_LABEL: [],
    }

    for record in records:
        severity = classify_record(record)
        groups[severity].append(record)

    return {
        "total": len(records),
        "critical": groups[CRITICAL_LABEL],
        "warning": groups[WARNING_LABEL],
        "healthy": groups[HEALTHY_LABEL],
    }


def format_days(days: float) -> str:
    """Return a grammatically correct day label for a leave balance."""
    amount = int(days) if days.is_integer() else days
    if abs(amount) == 1:
        return f"{amount} day"
    return f"{amount} days"


def format_group_lines(records: List[EmployeeRecord]) -> List[str]:
    """Format a list of employee records for console output."""
    lines: List[str] = []
    for record in sorted(records, key=lambda item: item.leave_balance):
        lines.append(f"• {record.name} ({format_days(record.leave_balance)})")
    return lines


def print_report(summary: Dict[str, object], elapsed_seconds: float) -> None:
    """Print the formatted leave balance report to the console."""
    critical = summary["critical"]
    warning = summary["warning"]
    healthy = summary["healthy"]
    generated_on = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    overall_status = "ATTENTION REQUIRED" if critical or warning else "ALL CLEAR"

    print("=" * 40)
    print("Employee Leave Balance Checker")
    print("=" * 40)
    print()
    print("Loading employee records...\n")

    for record in critical + warning + healthy:
        print(f"Checking {record.name}...")

    print("\n" + "=" * 40)
    print()
    print("Leave Balance Summary")
    print()
    print(f"Total Employees     : {summary['total']}")
    print(f"Healthy Balance     : {len(healthy)}")
    print(f"Low Leave (<{LOW_LEAVE_THRESHOLD} days) : {len(warning)}")
    print(f"Negative Balance    : {len(critical)}")
    print(f"Overall Status      : {overall_status}")
    print(f"Generated On        : {generated_on}")
    print()
    print("=" * 40)
    print()
    print("Employees Requiring Attention")
    print()

    if critical:
        print(CRITICAL_LABEL)
        print()
        print("\n".join(format_group_lines(critical)))
        print()

    if warning:
        print(WARNING_LABEL)
        print()
        print("\n".join(format_group_lines(warning)))
        print()

    print("Recommendations")
    print()
    print("1. Review employees with negative leave balances.")
    print("2. Verify approved leave records.")
    print("3. Coordinate with HR for leave reconciliation.")
    print()
    print("Report generated successfully.")
    print()
    print("Log File:")
    print(LOG_FILE)
    print()
    print(f"Execution Time: {elapsed_seconds:.3f} seconds")


def main() -> int:
    """Application entry point."""
    configure_logging()
    args = parse_arguments()
    csv_path = Path(args.csv)
    start_time = time.perf_counter()

    try:
        records = load_employee_records(csv_path)
    except (FileNotFoundError, ValueError, csv.Error) as error:
        logging.error("Failed to load records: %s", error)
        return 1
    except Exception as unexpected:
        logging.exception("Unexpected error while loading records")
        return 1

    if not records:
        logging.warning("No employee records found in %s", csv_path)

    summary = build_summary(records)
    elapsed_seconds = time.perf_counter() - start_time

    print_report(summary, elapsed_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
