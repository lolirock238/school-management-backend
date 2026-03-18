from app import create_app
from app.database import db
from app.models import User, Class, Subject, Attendance, Exam, ExamResult, Fee, Payment, Announcement, TimetableEntry, Coursework, Submission
from werkzeug.security import generate_password_hash
from datetime import date, datetime, timedelta

def seed_database():
    app = create_app()
    with app.app_context():
        # Clear existing data
        print("Clearing existing data...")
        db.drop_all()
        db.create_all()
        
        print("Creating test users...")
        
        # ========== CREATE ADMIN ==========
        admin = User(
            username='admin',
            email='admin@school.com',
            password_hash=generate_password_hash('admin123'),
            role='ADMIN',
            first_name='Admin',
            last_name='User',
            phone='+254700000001',
            department='Administration'
        )
        db.session.add(admin)
        
        # ========== CREATE TEACHER ==========
        teacher = User(
            username='teacher',
            email='teacher@school.com',
            password_hash=generate_password_hash('teacher123'),
            role='TEACHER',
            first_name='John',
            last_name='Teacher',
            phone='+254700000002',
            employee_id='TCH001',
            qualification='Masters in Mathematics',
            hire_date=date(2020, 1, 15)
        )
        db.session.add(teacher)
        db.session.flush()  # Get ID for teacher
        
        # ========== CREATE CLASS ==========
        class_1a = Class(
            name='Form 1A',
            academic_year='2024/2025',
            class_teacher_id=teacher.id,
            capacity=40
        )
        db.session.add(class_1a)
        db.session.flush()
        
        # ========== CREATE SUBJECTS ==========
        subjects = [
            {'name': 'Mathematics', 'code': 'MATH101', 'teacher': teacher},
            {'name': 'English', 'code': 'ENG101', 'teacher': teacher},
            {'name': 'Kiswahili', 'code': 'KIS101', 'teacher': teacher},
            {'name': 'Science', 'code': 'SCI101', 'teacher': teacher},
        ]
        
        subject_objects = []
        for s in subjects:
            subject = Subject(
                name=s['name'],
                code=s['code'],
                class_id=class_1a.id,
                teacher_id=s['teacher'].id
            )
            db.session.add(subject)
            subject_objects.append(subject)
        db.session.flush()
        
        # ========== CREATE STUDENTS ==========
        students_data = [
            {'first': 'Mike', 'last': 'Munene', 'adm': 'ADM001', 'gender': 'MALE'},
            {'first': 'Alice', 'last': 'Wanjiku', 'adm': 'ADM002', 'gender': 'FEMALE'},
            {'first': 'Brian', 'last': 'Odhiambo', 'adm': 'ADM003', 'gender': 'MALE'},
            {'first': 'Cynthia', 'last': 'Achieng', 'adm': 'ADM004', 'gender': 'FEMALE'},
        ]
        
        student_objects = []
        for s in students_data:
            student = User(
                username=s['adm'].lower(),
                email=f"{s['first'].lower()}@student.com",
                password_hash=generate_password_hash('student123'),
                role='STUDENT',
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
        
        # ========== CREATE PARENT ==========
        parent = User(
            username='parent',
            email='parent@school.com',
            password_hash=generate_password_hash('parent123'),
            role='PARENT',
            first_name='Robert',
            last_name='Parent',
            phone='+254700000003',
            occupation='Engineer'
        )
        db.session.add(parent)
        db.session.flush()
        
        # Link parent to first student (Mike)
        if student_objects:
            student_objects[0].parents.append(parent)
        
        # ========== CREATE ATTENDANCE RECORDS ==========
        today = date.today()
        for i, student in enumerate(student_objects):
            # Create attendance for last 5 days
            for days_ago in range(5):
                attendance_date = today - timedelta(days=days_ago)
                # Alternate status for variety
                status = 'PRESENT' if (i + days_ago) % 3 != 0 else 'ABSENT'
                
                attendance = Attendance(
                    student_id=student.id,
                    date=attendance_date,
                    status=status,
                    remarks=f"Attendance for {attendance_date}",
                    recorded_by=teacher.id,
                    recorded_at=datetime.now()
                )
                db.session.add(attendance)
        
        # ========== CREATE EXAMS AND RESULTS ==========
        exams = []
        for subject in subject_objects:
            exam = Exam(
                name=f"End Term 1 - {subject.name}",
                subject_id=subject.id,
                exam_date=date(2024, 4, 15),
                total_marks=100,
                pass_mark=50
            )
            db.session.add(exam)
            exams.append(exam)
        db.session.flush()
        
        # Create exam results for students
        for student in student_objects:
            for exam in exams:
                # Random marks between 40 and 95
                import random
                marks = random.randint(40, 95)
                
                # Determine grade
                if marks >= 80:
                    grade = 'A'
                elif marks >= 70:
                    grade = 'B'
                elif marks >= 60:
                    grade = 'C'
                elif marks >= 50:
                    grade = 'D'
                else:
                    grade = 'E'
                
                result = ExamResult(
                    exam_id=exam.id,
                    student_id=student.id,
                    marks_obtained=marks,
                    grade=grade,
                    remarks="Good performance" if marks >= 50 else "Needs improvement"
                )
                db.session.add(result)
        
        # ========== CREATE FEES AND PAYMENTS ==========
        for student in student_objects:
            fee = Fee(
                student_id=student.id,
                term="Term 1 2024",
                total_amount=50000,
                paid_amount=30000 if student.id == 3 else 45000,
                due_date=date(2024, 2, 15),
                status="partial" if student.id == 3 else "paid"
            )
            db.session.add(fee)
            db.session.flush()
            
            # Add payment records
            if student.id == 3:  # Mike - partial payment
                payment1 = Payment(
                    fee_id=fee.id,
                    amount=20000,
                    payment_date=datetime(2024, 1, 15),
                    payment_method="M-Pesa",
                    transaction_id=f"MPESA{student.id}001",
                    received_by=admin.id
                )
                db.session.add(payment1)
                
                payment2 = Payment(
                    fee_id=fee.id,
                    amount=10000,
                    payment_date=datetime(2024, 2, 10),
                    payment_method="Cash",
                    transaction_id=f"CASH{student.id}002",
                    received_by=admin.id
                )
                db.session.add(payment2)
            else:  # Others - full payment
                payment = Payment(
                    fee_id=fee.id,
                    amount=50000,
                    payment_date=datetime(2024, 1, 20),
                    payment_method="Bank Transfer",
                    transaction_id=f"BANK{student.id}001",
                    received_by=admin.id
                )
                db.session.add(payment)
        
        # ========== CREATE COURSEWORK (NEW) ==========
        print("Creating coursework and submissions...")
        
        coursework_types = ['ASSIGNMENT', 'CAT', 'ASSIGNMENT', 'CAT']
        coursework_titles = [
            'Algebra Problem Set',
            'Essay Writing',
            'Insha Writing',
            'Physics Practical Report'
        ]
        
        coursework_objects = []
        for i, subject in enumerate(subject_objects):
            coursework = Coursework(
                subject_id=subject.id,
                teacher_id=teacher.id,
                title=coursework_titles[i],
                description=f"Complete this {coursework_types[i].lower()} by the due date",
                type=coursework_types[i],
                due_date=datetime.now() + timedelta(days=7),
                total_marks=20 if coursework_types[i] == 'ASSIGNMENT' else 30
            )
            db.session.add(coursework)
            coursework_objects.append(coursework)
        db.session.flush()
        
        # ========== CREATE SUBMISSIONS (NEW) ==========
        for student in student_objects:
            for i, coursework in enumerate(coursework_objects):
                # Mike submits everything
                if student.id == 3:
                    submission = Submission(
                        coursework_id=coursework.id,
                        student_id=student.id,
                        content=f"This is my submission for {coursework.title}",
                        submission_date=datetime.now() - timedelta(days=2),
                        status='SUBMITTED'
                    )
                    db.session.add(submission)
                    
                    # Grade Mike's submissions
                    if coursework.id == coursework_objects[0].id:
                        submission.marks_obtained = 18
                        submission.feedback = "Good work, but show your working"
                        submission.status = 'GRADED'
                    elif coursework.id == coursework_objects[1].id:
                        submission.marks_obtained = 25
                        submission.feedback = "Excellent essay!"
                        submission.status = 'GRADED'
                
                # Alice submits some
                elif student.id == 4 and i < 2:
                    submission = Submission(
                        coursework_id=coursework.id,
                        student_id=student.id,
                        content=f"Here is my submission",
                        submission_date=datetime.now() - timedelta(days=1),
                        status='SUBMITTED'
                    )
                    db.session.add(submission)
        
        # ========== CREATE TIMETABLE ENTRIES ==========
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        times = [
            {'start': '08:00', 'end': '09:30'},
            {'start': '09:45', 'end': '11:15'},
            {'start': '11:30', 'end': '13:00'},
            {'start': '14:00', 'end': '15:30'},
        ]
        
        for i, subject in enumerate(subject_objects):
            timetable = TimetableEntry(
                class_id=class_1a.id,
                subject_id=subject.id,
                day_of_week=days[i % 5],
                start_time=datetime.strptime(times[i % 4]['start'], '%H:%M').time(),
                end_time=datetime.strptime(times[i % 4]['end'], '%H:%M').time(),
                room=f"Room {100 + i}"
            )
            db.session.add(timetable)
        
        # ========== CREATE ANNOUNCEMENTS ==========
        announcements = [
            {
                'title': 'School Closed for Holidays',
                'content': 'School will be closed from 20th December to 5th January',
                'target_role': None  # All users
            },
            {
                'title': 'Staff Meeting',
                'content': 'All teachers please attend meeting on Friday at 2pm',
                'target_role': 'TEACHER'
            },
            {
                'title': 'Parents Day',
                'content': 'Parents Day will be held on 15th March',
                'target_role': 'PARENT'
            }
        ]
        
        for ann in announcements:
            announcement = Announcement(
                title=ann['title'],
                content=ann['content'],
                target_role=ann['target_role'],
                created_by=admin.id,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=30)
            )
            db.session.add(announcement)
        
        # ========== COMMIT ALL CHANGES ==========
        db.session.commit()
        
        print("\n✅ DATABASE SEEDED SUCCESSFULLY!")
        print("=" * 50)
        print("LOGIN CREDENTIALS:")
        print("-" * 30)
        print("Admin  : admin / admin123")
        print("Teacher: teacher / teacher123")
        print("Student: ADM001 / student123 (Mike)")
        print("Student: ADM002 / student123 (Alice)")
        print("Student: ADM003 / student123 (Brian)")
        print("Student: ADM004 / student123 (Cynthia)")
        print("Parent : parent / parent123 (Robert - Mike's parent)")
        print("=" * 50)
        
        # Verify data
        print(f"\n📊 DATABASE STATS:")
        print(f"Users: {User.query.count()}")
        print(f"Students: {User.query.filter_by(role='STUDENT').count()}")
        print(f"Teachers: {User.query.filter_by(role='TEACHER').count()}")
        print(f"Classes: {Class.query.count()}")
        print(f"Subjects: {Subject.query.count()}")
        print(f"Courseworks: {Coursework.query.count()}")
        print(f"Submissions: {Submission.query.count()}")
        print(f"Attendance Records: {Attendance.query.count()}")
        print(f"Exam Results: {ExamResult.query.count()}")
        print(f"Fee Records: {Fee.query.count()}")
        print(f"Payments: {Payment.query.count()}")
        print(f"Timetable Entries: {TimetableEntry.query.count()}")
        print(f"Announcements: {Announcement.query.count()}")

if __name__ == '__main__':
    seed_database()