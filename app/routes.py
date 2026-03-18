from flask import jsonify, request, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from app.database import db
from app.models import User, Class, Subject, Attendance, Exam, ExamResult, Fee, Payment, Announcement, TimetableEntry, Coursework, Submission
from datetime import date, datetime

def init_routes(app):
    """Initialize routes with the app instance"""
    
    @app.route('/')
    def home():
        return jsonify({
            "message": "School Management System API",
            "status": "running"
        })

    @app.route('/health')
    def health():
        return jsonify({"status": "healthy"})

    # ========== AUTH ROUTES ==========
    @app.route('/auth/login', methods=['POST'])
    def login():
        data = request.get_json()
        
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'message': 'Missing credentials'}), 400
        
        user = User.query.filter_by(username=data['username']).first()
        
        if not user:
            return jsonify({'message': 'User not found'}), 401
        
        # Check password
        if not check_password_hash(user.password_hash, data['password']):
            return jsonify({'message': 'Invalid password'}), 401
        
        # Check role if provided (case-insensitive comparison)
        if data.get('role') and user.role.value.upper() != data['role'].upper():
            return jsonify({'message': 'Invalid role'}), 401
        
        return jsonify({
            'message': 'Login successful',
            'token': 'dummy-token-' + str(user.id),
            'user': {
                'id': user.id,
                'username': user.username,
                'name': f"{user.first_name or ''} {user.last_name or ''}".strip(),
                'role': user.role.value,
                'email': user.email
            }
        }), 200

    # ========== STUDENT ROUTES ==========
    @app.route('/api/students', methods=['GET'])
    def get_students():
        students = User.query.filter_by(role='STUDENT').all()
        result = []
        for s in students:
            result.append({
                'id': s.id,
                'first_name': s.first_name,
                'last_name': s.last_name,
                'admission_number': s.admission_number,
                'class_id': s.current_class_id,
                'class_name': s.class_.name if s.class_ else None,
                'gender': s.gender.value if s.gender else None,
                'email': s.email,
                'date_of_birth': s.date_of_birth.isoformat() if s.date_of_birth else None,
                'parent_name': s.parents[0].first_name + ' ' + s.parents[0].last_name if s.parents else None
            })
        return jsonify(result), 200

    @app.route('/api/students/<int:id>', methods=['GET'])
    def get_student(id):
        student = User.query.filter_by(id=id, role='STUDENT').first_or_404()
        return jsonify({
            'id': student.id,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'admission_number': student.admission_number,
            'class_id': student.current_class_id,
            'class_name': student.class_.name if student.class_ else None,
            'gender': student.gender.value if student.gender else None,
            'email': student.email,
            'date_of_birth': student.date_of_birth.isoformat() if student.date_of_birth else None
        }), 200

    @app.route('/api/students', methods=['POST'])
    def create_student():
        data = request.get_json()
        
        student = User(
            username=data.get('username') or data['admission_number'],
            email=data['email'],
            password_hash=generate_password_hash('default123'),
            role='STUDENT',
            first_name=data['first_name'],
            last_name=data['last_name'],
            gender=data.get('gender'),
            admission_number=data['admission_number'],
            date_of_birth=data.get('date_of_birth'),
            current_class_id=data.get('class_id')
        )
        db.session.add(student)
        db.session.commit()
        
        return jsonify({'message': 'Student created', 'id': student.id}), 201

    @app.route('/api/students/<int:id>', methods=['PUT'])
    def update_student(id):
        student = User.query.filter_by(id=id, role='STUDENT').first_or_404()
        data = request.get_json()
        
        student.first_name = data.get('first_name', student.first_name)
        student.last_name = data.get('last_name', student.last_name)
        student.email = data.get('email', student.email)
        student.gender = data.get('gender', student.gender)
        student.admission_number = data.get('admission_number', student.admission_number)
        student.date_of_birth = data.get('date_of_birth', student.date_of_birth)
        student.current_class_id = data.get('class_id', student.current_class_id)
        
        db.session.commit()
        return jsonify({'message': 'Student updated'}), 200

    @app.route('/api/students/<int:id>', methods=['DELETE'])
    def delete_student(id):
        student = User.query.filter_by(id=id, role='STUDENT').first_or_404()
        db.session.delete(student)
        db.session.commit()
        return jsonify({'message': 'Student deleted'}), 200

    # ========== TEACHER ROUTES ==========
    @app.route('/api/teachers', methods=['GET'])
    def get_teachers():
        teachers = User.query.filter_by(role='TEACHER').all()
        result = []
        for t in teachers:
            result.append({
                'id': t.id,
                'first_name': t.first_name,
                'last_name': t.last_name,
                'email': t.email,
                'employee_id': t.employee_id,
                'qualification': t.qualification,
                'phone': t.phone
            })
        return jsonify(result), 200

    # ========== CLASS ROUTES ==========
    @app.route('/api/classes', methods=['GET'])
    def get_classes():
        classes = Class.query.all()
        result = []
        for c in classes:
            class_teacher = User.query.get(c.class_teacher_id) if c.class_teacher_id else None
            student_count = User.query.filter_by(role='STUDENT', current_class_id=c.id).count()
            result.append({
                'id': c.id,
                'name': c.name,
                'academic_year': c.academic_year,
                'class_teacher_id': c.class_teacher_id,
                'class_teacher_name': f"{class_teacher.first_name} {class_teacher.last_name}" if class_teacher else None,
                'capacity': c.capacity,
                'student_count': student_count
            })
        return jsonify(result), 200

    # ========== SUBJECT ROUTES (NEW) ==========
    @app.route('/api/subjects', methods=['GET'])
    def get_subjects():
        subjects = Subject.query.all()
        result = []
        for s in subjects:
            result.append({
                'id': s.id,
                'name': s.name,
                'code': s.code,
                'class_id': s.class_id,
                'class_name': s.class_.name if s.class_ else None,
                'teacher_id': s.teacher_id,
                'teacher_name': f"{s.teacher.first_name} {s.teacher.last_name}" if s.teacher else None
            })
        return jsonify(result), 200

    @app.route('/api/subjects/class/<int:class_id>', methods=['GET'])
    def get_subjects_by_class(class_id):
        subjects = Subject.query.filter_by(class_id=class_id).all()
        result = []
        for s in subjects:
            result.append({
                'id': s.id,
                'name': s.name,
                'code': s.code,
                'teacher_name': f"{s.teacher.first_name} {s.teacher.last_name}" if s.teacher else None
            })
        return jsonify(result), 200

    # ========== STUDENT DASHBOARD ROUTES (NEW) ==========
    @app.route('/api/student/<int:student_id>/subjects', methods=['GET'])
    def get_student_subjects(student_id):
        student = User.query.filter_by(id=student_id, role='STUDENT').first_or_404()
        if not student.class_:
            return jsonify([]), 200
        
        subjects = Subject.query.filter_by(class_id=student.current_class_id).all()
        result = []
        for s in subjects:
            coursework_count = Coursework.query.filter_by(subject_id=s.id).count()
            result.append({
                'id': s.id,
                'name': s.name,
                'code': s.code,
                'teacher_name': f"{s.teacher.first_name} {s.teacher.last_name}" if s.teacher else None,
                'coursework_count': coursework_count
            })
        return jsonify(result), 200

    @app.route('/api/student/<int:student_id>/fees', methods=['GET'])
    def get_student_fees(student_id):
        fees = Fee.query.filter_by(student_id=student_id).all()
        result = []
        total_balance = 0
        for f in fees:
            balance = f.total_amount - f.paid_amount
            total_balance += balance
            result.append({
                'id': f.id,
                'term': f.term,
                'total_amount': f.total_amount,
                'paid_amount': f.paid_amount,
                'balance': balance,
                'status': f.status,
                'due_date': f.due_date.isoformat() if f.due_date else None
            })
        
        # Get payment history
        payments = Payment.query.join(Fee).filter(Fee.student_id == student_id).all()
        payment_history = []
        for p in payments:
            payment_history.append({
                'amount': p.amount,
                'date': p.payment_date.isoformat(),
                'method': p.payment_method,
                'transaction_id': p.transaction_id
            })
        
        return jsonify({
            'fees': result,
            'total_balance': total_balance,
            'payment_history': payment_history
        }), 200

    @app.route('/api/student/<int:student_id>/attendance', methods=['GET'])
    def get_student_attendance(student_id):
        attendance = Attendance.query.filter_by(student_id=student_id).order_by(Attendance.date.desc()).all()
        result = []
        present_count = 0
        for a in attendance:
            if a.status.value == 'present':
                present_count += 1
            result.append({
                'date': a.date.isoformat(),
                'status': a.status.value,
                'remarks': a.remarks
            })
        
        total = len(attendance)
        attendance_percentage = (present_count / total * 100) if total > 0 else 0
        
        return jsonify({
            'records': result,
            'percentage': round(attendance_percentage, 2),
            'present': present_count,
            'total': total
        }), 200

    @app.route('/api/student/<int:student_id>/courseworks', methods=['GET'])
    def get_student_courseworks(student_id):
        student = User.query.filter_by(id=student_id, role='STUDENT').first_or_404()
        if not student.class_:
            return jsonify([]), 200
        
        subjects = Subject.query.filter_by(class_id=student.current_class_id).all()
        subject_ids = [s.id for s in subjects]
        
        courseworks = Coursework.query.filter(Coursework.subject_id.in_(subject_ids)).order_by(Coursework.due_date).all()
        result = []
        for c in courseworks:
            submission = Submission.query.filter_by(coursework_id=c.id, student_id=student_id).first()
            result.append({
                'id': c.id,
                'title': c.title,
                'description': c.description,
                'type': c.type.value,
                'subject_name': c.subject.name,
                'teacher_name': f"{c.teacher.first_name} {c.teacher.last_name}",
                'due_date': c.due_date.isoformat() if c.due_date else None,
                'total_marks': c.total_marks,
                'submitted': submission is not None,
                'submission_id': submission.id if submission else None,
                'marks_obtained': submission.marks_obtained if submission else None,
                'feedback': submission.feedback if submission else None,
                'status': submission.status.value if submission else 'pending'
            })
        return jsonify(result), 200

    @app.route('/api/submit-coursework', methods=['POST'])
    def submit_coursework():
        data = request.get_json()
        
        submission = Submission(
            coursework_id=data['coursework_id'],
            student_id=data['student_id'],
            content=data.get('content'),
            file_path=data.get('file_path'),
            status='SUBMITTED'
        )
        db.session.add(submission)
        db.session.commit()
        
        return jsonify({'message': 'Submitted successfully', 'id': submission.id}), 201

    # ========== TEACHER DASHBOARD ROUTES (NEW) ==========
    @app.route('/api/teacher/<int:teacher_id>/subjects', methods=['GET'])
    def get_teacher_subjects(teacher_id):
        subjects = Subject.query.filter_by(teacher_id=teacher_id).all()
        result = []
        for s in subjects:
            student_count = User.query.filter_by(role='STUDENT', current_class_id=s.class_id).count()
            result.append({
                'id': s.id,
                'name': s.name,
                'code': s.code,
                'class_name': s.class_.name if s.class_ else None,
                'student_count': student_count
            })
        return jsonify(result), 200

    @app.route('/api/teacher/<int:teacher_id>/courseworks', methods=['GET'])
    def get_teacher_courseworks(teacher_id):
        courseworks = Coursework.query.filter_by(teacher_id=teacher_id).order_by(Coursework.created_at.desc()).all()
        result = []
        for c in courseworks:
            submissions = Submission.query.filter_by(coursework_id=c.id).all()
            graded_count = len([s for s in submissions if s.marks_obtained is not None])
            result.append({
                'id': c.id,
                'title': c.title,
                'description': c.description,
                'type': c.type.value,
                'subject_name': c.subject.name,
                'class_name': c.subject.class_.name,
                'due_date': c.due_date.isoformat() if c.due_date else None,
                'total_marks': c.total_marks,
                'submissions': len(submissions),
                'graded': graded_count
            })
        return jsonify(result), 200

    @app.route('/api/create-coursework', methods=['POST'])
    def create_coursework():
        data = request.get_json()
        
        coursework = Coursework(
            subject_id=data['subject_id'],
            teacher_id=data['teacher_id'],
            title=data['title'],
            description=data.get('description'),
            type=data['type'],
            due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
            total_marks=data.get('total_marks')
        )
        db.session.add(coursework)
        db.session.commit()
        
        return jsonify({'message': 'Coursework created', 'id': coursework.id}), 201

    @app.route('/api/teacher/<int:teacher_id>/timetable', methods=['GET'])
    def get_teacher_timetable(teacher_id):
        subjects = Subject.query.filter_by(teacher_id=teacher_id).all()
        subject_ids = [s.id for s in subjects]
        
        timetable = TimetableEntry.query.filter(TimetableEntry.subject_id.in_(subject_ids)).all()
        result = []
        for t in timetable:
            result.append({
                'id': t.id,
                'day': t.day_of_week,
                'start': t.start_time.isoformat() if t.start_time else None,
                'end': t.end_time.isoformat() if t.end_time else None,
                'subject': t.subject.name,
                'class': t.class_.name,
                'room': t.room
            })
        return jsonify(result), 200

    @app.route('/api/teacher/<int:teacher_id>/submissions/<int:coursework_id>', methods=['GET'])
    def get_submissions_for_grading(teacher_id, coursework_id):
        coursework = Coursework.query.filter_by(id=coursework_id, teacher_id=teacher_id).first_or_404()
        submissions = Submission.query.filter_by(coursework_id=coursework_id).all()
        result = []
        for s in submissions:
            result.append({
                'id': s.id,
                'student_name': f"{s.student.first_name} {s.student.last_name}",
                'admission': s.student.admission_number,
                'submission_date': s.submission_date.isoformat(),
                'content': s.content,
                'file_path': s.file_path,
                'marks_obtained': s.marks_obtained,
                'feedback': s.feedback,
                'status': s.status.value
            })
        return jsonify(result), 200

    @app.route('/api/grade-submission', methods=['POST'])
    def grade_submission():
        data = request.get_json()
        
        submission = Submission.query.get(data['submission_id'])
        submission.marks_obtained = data['marks_obtained']
        submission.feedback = data.get('feedback')
        submission.status = 'GRADED'
        
        db.session.commit()
        return jsonify({'message': 'Submission graded successfully'}), 200

    # ========== PARENT DASHBOARD ROUTES (NEW) ==========
    @app.route('/api/parent/<int:parent_id>/children', methods=['GET'])
    def get_parent_children(parent_id):
        parent = User.query.filter_by(id=parent_id, role='PARENT').first_or_404()
        result = []
        for child in parent.children:
            # Get child's grades
            exam_results = ExamResult.query.filter_by(student_id=child.id).all()
            grades = []
            for e in exam_results:
                grades.append({
                    'exam': e.exam.name,
                    'subject': e.exam.subject.name,
                    'marks': e.marks_obtained,
                    'grade': e.grade
                })
            
            # Get child's attendance
            attendance = Attendance.query.filter_by(student_id=child.id).count()
            present = Attendance.query.filter_by(student_id=child.id, status='PRESENT').count()
            attendance_percentage = (present / attendance * 100) if attendance > 0 else 0
            
            # Get child's fees
            fees = Fee.query.filter_by(student_id=child.id).all()
            total_fees = sum(f.total_amount for f in fees)
            paid_fees = sum(f.paid_amount for f in fees)
            
            # Get child's coursework submissions
            submissions = Submission.query.filter_by(student_id=child.id).all()
            coursework_stats = []
            for sub in submissions:
                coursework_stats.append({
                    'title': sub.coursework.title,
                    'subject': sub.coursework.subject.name,
                    'marks': sub.marks_obtained,
                    'feedback': sub.feedback
                })
            
            result.append({
                'id': child.id,
                'name': f"{child.first_name} {child.last_name}",
                'admission': child.admission_number,
                'class': child.class_.name if child.class_ else None,
                'grades': grades,
                'attendance_percentage': round(attendance_percentage, 2),
                'fee_balance': total_fees - paid_fees,
                'courseworks': coursework_stats
            })
        return jsonify(result), 200

    # ========== DASHBOARD ROUTES ==========
    @app.route('/api/dashboard/stats', methods=['GET'])
    def get_dashboard_stats():
        total_students = User.query.filter_by(role='STUDENT').count()
        total_teachers = User.query.filter_by(role='TEACHER').count()
        total_classes = Class.query.count()
        
        return jsonify({
            'totalStudents': total_students,
            'totalTeachers': total_teachers,
            'totalClasses': total_classes,
            'todayAttendance': '85%'
        }), 200

    @app.route('/api/dashboard/recent-students', methods=['GET'])
    def get_recent_students():
        students = User.query.filter_by(role='STUDENT').order_by(User.id.desc()).limit(5).all()
        result = []
        for s in students:
            result.append({
                'name': f"{s.first_name} {s.last_name}",
                'admission_number': s.admission_number
            })
        return jsonify(result), 200

    @app.route('/api/dashboard/upcoming-exams', methods=['GET'])
    def get_upcoming_exams():
        exams = Exam.query.order_by(Exam.exam_date).limit(5).all()
        result = []
        for e in exams:
            result.append({
                'name': e.name,
                'date': e.exam_date.isoformat() if e.exam_date else None
            })
        return jsonify(result), 200

    @app.route('/api/dashboard/pending-fees', methods=['GET'])
    def get_pending_fees():
        fees = Fee.query.filter(Fee.status != 'paid').limit(5).all()
        result = []
        for f in fees:
            student = User.query.get(f.student_id)
            result.append({
                'student_name': f"{student.first_name} {student.last_name}" if student else 'Unknown',
                'balance': f.total_amount - f.paid_amount
            })
        return jsonify(result), 200

    return app