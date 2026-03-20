from app import create_app
from app.database import db
from app.models import (User, Class, Subject, Attendance, Exam, ExamResult,
                        Fee, Payment, Announcement, TimetableEntry, Coursework,
                        Submission, UserRole, Gender, AttendanceStatus,
                        CourseworkType, SubmissionStatus, student_parent)
from werkzeug.security import generate_password_hash
from datetime import date, datetime, timedelta
import random


def seed_database():
    app = create_app()
    with app.app_context():

        print("Clearing existing data...")

        # Delete in reverse dependency order — DO NOT use db.drop_all()
        Submission.query.delete()
        Coursework.query.delete()
        Payment.query.delete()
        Fee.query.delete()
        ExamResult.query.delete()
        Exam.query.delete()
        Attendance.query.delete()
        TimetableEntry.query.delete()
        Announcement.query.delete()
        Subject.query.delete()
        Class.query.delete()

        # Clear the many-to-many association table
        db.session.execute(student_parent.delete())

        # Delete users in safe order
        User.query.filter_by(role=UserRole.STUDENT).delete()
        User.query.filter_by(role=UserRole.PARENT).delete()
        User.query.filter_by(role=UserRole.TEACHER).delete()
        User.query.filter_by(role=UserRole.ADMIN).delete()

        db.session.commit()
        print("Data cleared. Seeding fresh data...")

        # ===== ADMIN =====
        admin = User(
            username='admin',
            email='admin@school.com',
            password_hash=generate_password_hash('admin123'),
            role=UserRole.ADMIN,
            first_name='Admin',
            last_name='User',
            phone='+254700000001',
            department='Administration'
        )
        db.session.add(admin)

        # ===== TEACHER =====
        teacher = User(
            username='teacher',
            email='teacher@school.com',
            password_hash=generate_password_hash('teacher123'),
            role=UserRole.TEACHER,
            first_name='John',
            last_name='Kamau',
            phone='+254700000002',
            employee_id='TCH001',
            qualification='Masters in Mathematics',
            hire_date=date(2020, 1, 15)
        )
        db.session.add(teacher)
        db.session.flush()

        # ===== CLASS =====
        class_1a = Class(
            name='Form 1A',
            academic_year='2024/2025',
            class_teacher_id=teacher.id,
            capacity=40
        )
        db.session.add(class_1a)
        db.session.flush()

        # ===== SUBJECTS =====
        subject_data = [
            {'name': 'Mathematics', 'code': 'MATH101'},
            {'name': 'English',     'code': 'ENG101'},
            {'name': 'Kiswahili',   'code': 'KIS101'},
            {'name': 'Science',     'code': 'SCI101'},
        ]
        subject_objects = []
        for s in subject_data:
            subj = Subject(
                name=s['name'],
                code=s['code'],
                class_id=class_1a.id,
                teacher_id=teacher.id
            )
            db.session.add(subj)
            subject_objects.append(subj)
        db.session.flush()

        # ===== STUDENTS =====
        students_data = [
            {'first': 'Mike',    'last': 'Munene',   'adm': 'ADM001', 'gender': Gender.MALE},
            {'first': 'Alice',   'last': 'Wanjiku',  'adm': 'ADM002', 'gender': Gender.FEMALE},
            {'first': 'Brian',   'last': 'Odhiambo', 'adm': 'ADM003', 'gender': Gender.MALE},
            {'first': 'Cynthia', 'last': 'Achieng',  'adm': 'ADM004', 'gender': Gender.FEMALE},
        ]
        student_objects = []
        for s in students_data:
            student = User(
                username=s['adm'].lower(),
                email=f"{s['first'].lower()}@student.com",
                password_hash=generate_password_hash('student123'),
                role=UserRole.STUDENT,
                first_name=s['first'],
                last_name=s['last'],
                gender=s['gender'],
                admission_number=s['adm'],
                date_of_birth=date(2005, 3, 15),
                enrollment_date=date(2024, 1, 10),
                current_class_id=class_1a.id
            )
            db.session.add(student)
            student_objects.append(student)
        db.session.flush()

        # ===== PARENTS (one per student) =====
        parents_data = [
            {
                'username': 'parent.munene',
                'email': 'robert.munene@email.com',
                'first_name': 'Robert',
                'last_name': 'Munene',
                'phone': '+254700000003',
                'occupation': 'Engineer',
                'password': 'parent123',
                'child_index': 0   # Mike
            },
            {
                'username': 'parent.wanjiku',
                'email': 'grace.wanjiku@email.com',
                'first_name': 'Grace',
                'last_name': 'Wanjiku',
                'phone': '+254700000004',
                'occupation': 'Teacher',
                'password': 'parent123',
                'child_index': 1   # Alice
            },
            {
                'username': 'parent.odhiambo',
                'email': 'peter.odhiambo@email.com',
                'first_name': 'Peter',
                'last_name': 'Odhiambo',
                'phone': '+254700000005',
                'occupation': 'Doctor',
                'password': 'parent123',
                'child_index': 2   # Brian
            },
            {
                'username': 'parent.achieng',
                'email': 'mary.achieng@email.com',
                'first_name': 'Mary',
                'last_name': 'Achieng',
                'phone': '+254700000006',
                'occupation': 'Accountant',
                'password': 'parent123',
                'child_index': 3   # Cynthia
            },
        ]

        parent_objects = []
        for p in parents_data:
            parent = User(
                username=p['username'],
                email=p['email'],
                password_hash=generate_password_hash(p['password']),
                role=UserRole.PARENT,
                first_name=p['first_name'],
                last_name=p['last_name'],
                phone=p['phone'],
                occupation=p['occupation'],
            )
            db.session.add(parent)
            parent_objects.append(parent)
        db.session.flush()

        # Link each parent to their child
        for p_data, parent in zip(parents_data, parent_objects):
            child = student_objects[p_data['child_index']]
            child.parents.append(parent)

        # ===== ATTENDANCE (30 days, weekends skipped) =====
        today = date.today()
        for i, student in enumerate(student_objects):
            for days_ago in range(30):
                att_date = today - timedelta(days=days_ago)
                if att_date.weekday() >= 5:
                    continue
                if (i + days_ago) % 5 == 0:
                    status = AttendanceStatus.ABSENT
                elif (i + days_ago) % 7 == 0:
                    status = AttendanceStatus.LATE
                else:
                    status = AttendanceStatus.PRESENT

                db.session.add(Attendance(
                    student_id=student.id,
                    date=att_date,
                    status=status,
                    remarks=f"Attendance for {att_date}",
                    recorded_by=teacher.id,
                    recorded_at=datetime.now()
                ))

        # ===== EXAMS & RESULTS =====
        exams = []
        for subj in subject_objects:
            exam = Exam(
                name=f"End Term 1 - {subj.name}",
                subject_id=subj.id,
                exam_date=date(2024, 4, 15),
                total_marks=100,
                pass_mark=50
            )
            db.session.add(exam)
            exams.append(exam)
        db.session.flush()

        for student in student_objects:
            for exam in exams:
                marks = random.randint(40, 95)
                grade = (
                    'A' if marks >= 80 else
                    'B' if marks >= 70 else
                    'C' if marks >= 60 else
                    'D' if marks >= 50 else 'E'
                )
                db.session.add(ExamResult(
                    exam_id=exam.id,
                    student_id=student.id,
                    marks_obtained=marks,
                    grade=grade,
                    remarks="Good performance" if marks >= 50 else "Needs improvement"
                ))

        # ===== FEES & PAYMENTS =====
        for i, student in enumerate(student_objects):
            is_partial = (i == 0)   # Mike has partial payment
            paid_amount = 30000 if is_partial else 50000
            fee = Fee(
                student_id=student.id,
                term="Term 1 2024",
                total_amount=50000,
                paid_amount=paid_amount,
                due_date=date(2024, 2, 15),
                status="partial" if is_partial else "paid"
            )
            db.session.add(fee)
            db.session.flush()

            if is_partial:
                db.session.add(Payment(
                    fee_id=fee.id,
                    amount=20000,
                    payment_date=datetime(2024, 1, 15),
                    payment_method="M-Pesa",
                    transaction_id=f"MPESA{student.id}001",
                    received_by=admin.id
                ))
                db.session.add(Payment(
                    fee_id=fee.id,
                    amount=10000,
                    payment_date=datetime(2024, 2, 10),
                    payment_method="Cash",
                    transaction_id=f"CASH{student.id}002",
                    received_by=admin.id
                ))
            else:
                db.session.add(Payment(
                    fee_id=fee.id,
                    amount=50000,
                    payment_date=datetime(2024, 1, 20),
                    payment_method="Bank Transfer",
                    transaction_id=f"BANK{student.id}001",
                    received_by=admin.id
                ))

        # ===== COURSEWORK =====
        print("Creating coursework and submissions...")
        coursework_config = [
            {'title': 'Algebra Problem Set',     'type': CourseworkType.ASSIGNMENT, 'marks': 20},
            {'title': 'Essay Writing',            'type': CourseworkType.CAT,        'marks': 30},
            {'title': 'Insha Writing',            'type': CourseworkType.ASSIGNMENT, 'marks': 20},
            {'title': 'Physics Practical Report', 'type': CourseworkType.CAT,        'marks': 30},
        ]
        coursework_objects = []
        for i, subj in enumerate(subject_objects):
            cfg = coursework_config[i]
            cw = Coursework(
                subject_id=subj.id,
                teacher_id=teacher.id,
                title=cfg['title'],
                description=f"Complete this {cfg['type'].value} by the due date",
                type=cfg['type'],
                due_date=datetime.now() + timedelta(days=7),
                total_marks=cfg['marks']
            )
            db.session.add(cw)
            coursework_objects.append(cw)
        db.session.flush()

        # ===== SUBMISSIONS =====
        for student in student_objects:
            for i, cw in enumerate(coursework_objects):
                if student.username == 'adm001':
                    sub = Submission(
                        coursework_id=cw.id,
                        student_id=student.id,
                        content=f"My submission for {cw.title}",
                        submission_date=datetime.now() - timedelta(days=2),
                        status=SubmissionStatus.SUBMITTED
                    )
                    db.session.add(sub)
                    db.session.flush()
                    if i == 0:
                        sub.marks_obtained = 18
                        sub.feedback = "Good work, but show your working"
                        sub.status = SubmissionStatus.GRADED
                    elif i == 1:
                        sub.marks_obtained = 25
                        sub.feedback = "Excellent essay!"
                        sub.status = SubmissionStatus.GRADED

                elif student.username == 'adm002' and i < 2:
                    db.session.add(Submission(
                        coursework_id=cw.id,
                        student_id=student.id,
                        content="Here is my submission",
                        submission_date=datetime.now() - timedelta(days=1),
                        status=SubmissionStatus.SUBMITTED
                    ))

        # ===== TIMETABLE =====
        days  = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        times = [
            ('08:00', '09:30'),
            ('09:45', '11:15'),
            ('11:30', '13:00'),
            ('14:00', '15:30'),
        ]
        for i, subj in enumerate(subject_objects):
            start, end = times[i % 4]
            db.session.add(TimetableEntry(
                class_id=class_1a.id,
                subject_id=subj.id,
                day_of_week=days[i % 5],
                start_time=datetime.strptime(start, '%H:%M').time(),
                end_time=datetime.strptime(end,   '%H:%M').time(),
                room=f"Room {100 + i}"
            ))

        # ===== ANNOUNCEMENTS =====
        announcements_data = [
            {
                'title': 'School Closed for Holidays',
                'content': 'School will be closed from 20th December to 5th January. '
                           'All students must clear fees before the break.',
                'target_role': None,
            },
            {
                'title': 'Staff Meeting',
                'content': 'All teachers please attend the mandatory meeting on Friday at 2:00 PM.',
                'target_role': UserRole.TEACHER,
            },
            {
                'title': 'Parents Day — 15th March',
                'content': "You are warmly invited to our annual Parents Day. "
                           "Come celebrate your child's achievements!",
                'target_role': UserRole.PARENT,
            },
        ]
        for ann in announcements_data:
            db.session.add(Announcement(
                title=ann['title'],
                content=ann['content'],
                target_role=ann['target_role'],
                created_by=admin.id,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=60)
            ))

        db.session.commit()

        # ===== SUMMARY =====
        print("\n✅ DATABASE SEEDED SUCCESSFULLY!")
        print("=" * 55)
        print("LOGIN CREDENTIALS:")
        print("-" * 55)
        print("Admin   : admin          / admin123")
        print("Teacher : teacher        / teacher123")
        print("-" * 55)
        print("Student : adm001         / student123  (Mike Munene)")
        print("Student : adm002         / student123  (Alice Wanjiku)")
        print("Student : adm003         / student123  (Brian Odhiambo)")
        print("Student : adm004         / student123  (Cynthia Achieng)")
        print("-" * 55)
        print("Parent  : parent.munene  / parent123   (Robert  → Mike)")
        print("Parent  : parent.wanjiku / parent123   (Grace   → Alice)")
        print("Parent  : parent.odhiambo/ parent123   (Peter   → Brian)")
        print("Parent  : parent.achieng / parent123   (Mary    → Cynthia)")
        print("=" * 55)
        print("\n📊 DATABASE STATS:")
        print(f"  Users             : {User.query.count()}")
        print(f"  Students          : {User.query.filter_by(role=UserRole.STUDENT).count()}")
        print(f"  Teachers          : {User.query.filter_by(role=UserRole.TEACHER).count()}")
        print(f"  Parents           : {User.query.filter_by(role=UserRole.PARENT).count()}")
        print(f"  Classes           : {Class.query.count()}")
        print(f"  Subjects          : {Subject.query.count()}")
        print(f"  Courseworks       : {Coursework.query.count()}")
        print(f"  Submissions       : {Submission.query.count()}")
        print(f"  Attendance Records: {Attendance.query.count()}")
        print(f"  Exam Results      : {ExamResult.query.count()}")
        print(f"  Fee Records       : {Fee.query.count()}")
        print(f"  Payments          : {Payment.query.count()}")
        print(f"  Timetable Entries : {TimetableEntry.query.count()}")
        print(f"  Announcements     : {Announcement.query.count()}")


if __name__ == '__main__':
    seed_database()