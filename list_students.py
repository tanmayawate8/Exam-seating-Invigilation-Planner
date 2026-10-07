"""
Utility script to display imported students in the database.
Usage: python list_students.py
"""

from app import create_app
from app.models.student import Student

app = create_app('development')
with app.app_context():
    students = Student.query.filter_by(class_name='TYCO', division='C').order_by(Student.sr_no).all()
    total = len(students)
    
    print("\n" + "=" * 95)
    print(f"--- TYCO Division C - Imported Student Roll-Call List (Total: {total}) ---")
    print("=" * 95)
    header = f"{'Sr':<4} | {'Roll No':<8} | {'Enrollment No':<14} | {'Batch':<6} | {'Student Name':<34} | {'Contact':<12}"
    print(header)
    print("-" * 95)
    
    for s in students:
        sr = s.sr_no if s.sr_no is not None else "-"
        roll = s.roll_number or "-"
        enr = s.enrollment_number or "-"
        batch = s.batch or "-"
        name = s.name or s.full_name
        contact = s.student_contact or "N/A"
        print(f"{sr:<4} | {roll:<8} | {enr:<14} | {batch:<6} | {name:<34} | {contact:<12}")
    
    print("=" * 95)
    c1 = sum(1 for s in students if s.batch == 'C1')
    c2 = sum(1 for s in students if s.batch == 'C2')
    print(f"Batch C1 Count: {c1} | Batch C2 Count: {c2} | Total: {total}\n")
