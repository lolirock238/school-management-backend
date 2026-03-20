from flask import jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash
from app.database import db
from app.models import (User, Class, Subject, Attendance, Exam, ExamResult,
                        Fee, Payment, Announcement, TimetableEntry, Coursework,
                        Submission, UserRole, Gender, AttendanceStatus,
                        CourseworkType, SubmissionStatus)
from datetime import datetime


def init_routes(app):

    @app.route('/')
    def home():
        return jsonify({"message": "School Management System API", "status": "running"})

    @app.route('/health')
    def health():
        return jsonify({"status": "healthy"})

    # =========================================================
    #  AUTH
    # =========================================================
    @app.route('/auth/login', methods=['POST'])
    def login():
        data = request.get_json()
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'message': 'Missing credentials'}), 400

        user = User.query.filter_by(username=data['username']).first()
        if not user:
            return jsonify({'message': 'User not found'}), 401

        if not check_password_hash(user.password_hash, data['password']):
            return jsonify({'message': 'Invalid password'}), 401

        if data.get('role') and user.role.value.upper() != data['role'].upper():
            return jsonify({'message': 'Invalid role for this user'}), 401

        return jsonify({
            'message': 'Login successful',
            'token': f'token-{user.id}',
            'user': {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'name': f"{user.first_name or ''} {user.last_name or ''}".strip(),
                'role': user.role.value,
                'email': user.email,
            }
        }), 200

    # =========================================================
    #  STUDENTS
    # =========================================================
    @app.route('/api/students', methods=['GET'])
    def get_students():
        students = User.query.filter_by(role=UserRole.STUDENT).all()
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
                'phone': s.phone,
                'address': s.address,
                'date_of_birth': s.date_of_birth.isoformat() if s.date_of_birth else None,
                'parent_id': s.parents[0].id if s.parents else None,
                'parent_name': (
                    f"{s.parents[0].first_name} {s.parents[0].last_name}"
                    if s.parents else None
                ),
            })
        return jsonify(result), 200

    @app.route('/api/students/<int:id>', methods=['GET'])
    def get_student(id):
        s = User.query.filter_by(id=id, role=UserRole.STUDENT).first_or_404()
        return jsonify({
            'id': s.id,
            'first_name': s.first_name,
            'last_name': s.last_name,
            'admission_number': s.admission_number,
            'class_id': s.current_class_id,
            'class_name': s.class_.name if s.class_ else None,
            'gender': s.gender.value if s.gender else None,
            'email': s.email,
            'phone': s.phone,
            'address': s.address,
            'date_of_birth': s.date_of_birth.isoformat() if s.date_of_birth else None,
            'parent_id': s.parents[0].id if s.parents else None,
            'parent_name': (
                f"{s.parents[0].first_name} {s.parents[0].last_name}"
                if s.parents else None
            ),
        }), 200

    @app.route('/api/students', methods=['POST'])
    def create_student():
        data = request.get_json()

        if not data.get('first_name') or not data.get('admission_number'):
            return jsonify({'message': 'first_name and admission_number are required'}), 400

        if User.query.filter_by(admission_number=data['admission_number']).first():
            return jsonify({'message': 'Admission number already exists'}), 409

        # Parse gender enum safely
        gender = None
        if data.get('gender'):
            try:
                gender = Gender[data['gender'].upper()]
            except KeyError:
                gender = None

        # Auto-generate username from admission number if not provided
        username = data.get('username') or data['admission_number'].lower()
        base = username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base}{counter}"
            counter += 1

        student = User(
            username=username,
            email=data.get('email') or f"{data['admission_number'].lower()}@school.ac.ke",
            password_hash=generate_password_hash('student123'),
            role=UserRole.STUDENT,
            first_name=data['first_name'],
            last_name=data.get('last_name', ''),
            gender=gender,
            admission_number=data['admission_number'],
            date_of_birth=data.get('date_of_birth'),
            current_class_id=data.get('class_id'),
            phone=data.get('phone'),
            address=data.get('address'),
        )
        db.session.add(student)
        db.session.flush()

        # Link parent if provided
        if data.get('parent_id'):
            parent = User.query.filter_by(
                id=data['parent_id'], role=UserRole.PARENT
            ).first()
            if parent:
                student.parents.append(parent)

        db.session.commit()
        return jsonify({'message': 'Student created', 'id': student.id}), 201

    @app.route('/api/students/<int:id>', methods=['PUT'])
    def update_student(id):
        student = User.query.filter_by(id=id, role=UserRole.STUDENT).first_or_404()
        data = request.get_json()

        # Parse gender enum safely
        if data.get('gender'):
            try:
                student.gender = Gender[data['gender'].upper()]
            except KeyError:
                pass
        
        student.first_name       = data.get('first_name',       student.first_name)
        student.last_name        = data.get('last_name',        student.last_name)
        student.email            = data.get('email',            student.email)
        student.admission_number = data.get('admission_number', student.admission_number)
        student.date_of_birth    = data.get('date_of_birth',   student.date_of_birth)
        student.current_class_id = data.get('class_id',        student.current_class_id)
        student.phone            = data.get('phone',            student.phone)
        student.address          = data.get('address',          student.address)

        # Update parent link
        if 'parent_id' in data:
            # Remove all existing parent links first
            student.parents.clear()
            if data['parent_id']:
                parent = User.query.filter_by(
                    id=data['parent_id'], role=UserRole.PARENT
                ).first()
                if parent:
                    student.parents.append(parent)

        db.session.commit()
        return jsonify({'message': 'Student updated'}), 200

    @app.route('/api/students/<int:id>', methods=['DELETE'])
    def delete_student(id):
        student = User.query.filter_by(id=id, role=UserRole.STUDENT).first_or_404()
        db.session.delete(student)
        db.session.commit()
        return jsonify({'message': 'Student deleted'}), 200

    # =========================================================
    #  TEACHERS
    # =========================================================
    @app.route('/api/teachers', methods=['GET'])
    def get_teachers():
        teachers = User.query.filter_by(role=UserRole.TEACHER).all()
        result = []
        for t in teachers:
            subjects = [s.name for s in t.subjects_taught]
            result.append({
                'id': t.id,
                'first_name': t.first_name,
                'last_name': t.last_name,
                'email': t.email,
                'employee_id': t.employee_id,
                'qualification': t.qualification,
                'phone': t.phone,
                'subjects': ', '.join(subjects) if subjects else None,
            })
        return jsonify(result), 200

    @app.route('/api/teachers/<int:id>', methods=['GET'])
    def get_teacher(id):
        t = User.query.filter_by(id=id, role=UserRole.TEACHER).first_or_404()
        subjects = [s.name for s in t.subjects_taught]
        return jsonify({
            'id': t.id,
            'first_name': t.first_name,
            'last_name': t.last_name,
            'email': t.email,
            'employee_id': t.employee_id,
            'qualification': t.qualification,
            'phone': t.phone,
            'subjects': ', '.join(subjects) if subjects else None,
        }), 200

    @app.route('/api/teachers', methods=['POST'])
    def create_teacher():
        data = request.get_json()

        if not data.get('first_name') or not data.get('last_name') or not data.get('email'):
            return jsonify({'message': 'first_name, last_name and email are required'}), 400

        if User.query.filter_by(email=data['email']).first():
            return jsonify({'message': 'Email already exists'}), 409

        if data.get('employee_id') and User.query.filter_by(
                employee_id=data['employee_id']).first():
            return jsonify({'message': 'Employee ID already exists'}), 409

        username = data.get('username') or (
            data['first_name'].lower() + '.' + data['last_name'].lower()
        )
        base = username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base}{counter}"
            counter += 1

        teacher = User(
            username=username,
            email=data['email'],
            password_hash=generate_password_hash(data.get('password', 'teacher123')),
            role=UserRole.TEACHER,
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data.get('phone'),
            employee_id=data.get('employee_id'),
            qualification=data.get('qualification'),
        )
        db.session.add(teacher)
        db.session.commit()
        return jsonify({'message': 'Teacher created', 'id': teacher.id}), 201

    @app.route('/api/teachers/<int:id>', methods=['PUT'])
    def update_teacher(id):
        teacher = User.query.filter_by(id=id, role=UserRole.TEACHER).first_or_404()
        data = request.get_json()

        teacher.first_name    = data.get('first_name',    teacher.first_name)
        teacher.last_name     = data.get('last_name',     teacher.last_name)
        teacher.email         = data.get('email',         teacher.email)
        teacher.phone         = data.get('phone',         teacher.phone)
        teacher.employee_id   = data.get('employee_id',   teacher.employee_id)
        teacher.qualification = data.get('qualification', teacher.qualification)

        db.session.commit()
        return jsonify({'message': 'Teacher updated'}), 200

    @app.route('/api/teachers/<int:id>', methods=['DELETE'])
    def delete_teacher(id):
        teacher = User.query.filter_by(id=id, role=UserRole.TEACHER).first_or_404()
        db.session.delete(teacher)
        db.session.commit()
        return jsonify({'message': 'Teacher deleted'}), 200

    # =========================================================
    #  PARENTS
    # =========================================================
    @app.route('/api/parents', methods=['GET'])
    def get_parents():
        parents = User.query.filter_by(role=UserRole.PARENT).all()
        result = []
        for p in parents:
            result.append({
                'id': p.id,
                'first_name': p.first_name,
                'last_name': p.last_name,
                'email': p.email,
                'phone': p.phone,
                'address': p.address,
                'occupation': p.occupation,
                'children_count': len(p.children),
            })
        return jsonify(result), 200

    @app.route('/api/parents/<int:id>', methods=['GET'])
    def get_parent(id):
        p = User.query.filter_by(id=id, role=UserRole.PARENT).first_or_404()
        return jsonify({
            'id': p.id,
            'first_name': p.first_name,
            'last_name': p.last_name,
            'email': p.email,
            'phone': p.phone,
            'address': p.address,
            'occupation': p.occupation,
        }), 200

    @app.route('/api/parents', methods=['POST'])
    def create_parent():
        data = request.get_json()

        if not data.get('first_name') or not data.get('last_name') or not data.get('email'):
            return jsonify({'message': 'first_name, last_name and email are required'}), 400

        if User.query.filter_by(email=data['email']).first():
            return jsonify({'message': 'Email already exists'}), 409

        username = data.get('username') or (
            data['first_name'].lower() + '.' + data['last_name'].lower()
        )
        base = username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base}{counter}"
            counter += 1

        parent = User(
            username=username,
            email=data['email'],
            password_hash=generate_password_hash(data.get('password', 'parent123')),
            role=UserRole.PARENT,
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data.get('phone'),
            address=data.get('address'),
            occupation=data.get('occupation'),
        )
        db.session.add(parent)
        db.session.commit()

        return jsonify({
            'message': 'Parent created successfully',
            'id': parent.id,
            'first_name': parent.first_name,
            'last_name': parent.last_name,
        }), 201

    @app.route('/api/parents/<int:id>', methods=['PUT'])
    def update_parent(id):
        parent = User.query.filter_by(id=id, role=UserRole.PARENT).first_or_404()
        data = request.get_json()

        parent.first_name = data.get('first_name', parent.first_name)
        parent.last_name  = data.get('last_name',  parent.last_name)
        parent.email      = data.get('email',      parent.email)
        parent.phone      = data.get('phone',      parent.phone)
        parent.address    = data.get('address',    parent.address)
        parent.occupation = data.get('occupation', parent.occupation)

        db.session.commit()
        return jsonify({'message': 'Parent updated'}), 200

    @app.route('/api/parents/<int:id>', methods=['DELETE'])
    def delete_parent(id):
        parent = User.query.filter_by(id=id, role=UserRole.PARENT).first_or_404()
        db.session.delete(parent)
        db.session.commit()
        return jsonify({'message': 'Parent deleted'}), 200

    # =========================================================
    #  CLASSES
    # =========================================================
    @app.route('/api/classes', methods=['GET'])
    def get_classes():
        classes = Class.query.all()
        result = []
        for c in classes:
            teacher = User.query.get(c.class_teacher_id) if c.class_teacher_id else None
            student_count = User.query.filter_by(
                role=UserRole.STUDENT, current_class_id=c.id
            ).count()
            result.append({
                'id': c.id,
                'name': c.name,
                'academic_year': c.academic_year,
                'class_teacher_id': c.class_teacher_id,
                'class_teacher_name': (
                    f"{teacher.first_name} {teacher.last_name}" if teacher else None
                ),
                'capacity': c.capacity,
                'student_count': student_count,
            })
        return jsonify(result), 200

    @app.route('/api/classes/<int:id>', methods=['GET'])
    def get_class(id):
        c = Class.query.get_or_404(id)
        teacher = User.query.get(c.class_teacher_id) if c.class_teacher_id else None
        student_count = User.query.filter_by(
            role=UserRole.STUDENT, current_class_id=c.id
        ).count()
        return jsonify({
            'id': c.id,
            'name': c.name,
            'academic_year': c.academic_year,
            'class_teacher_id': c.class_teacher_id,
            'class_teacher_name': (
                f"{teacher.first_name} {teacher.last_name}" if teacher else None
            ),
            'capacity': c.capacity,
            'student_count': student_count,
        }), 200

    @app.route('/api/classes', methods=['POST'])
    def create_class():
        data = request.get_json()
        if not data.get('name'):
            return jsonify({'message': 'Class name is required'}), 400

        new_class = Class(
            name=data['name'],
            academic_year=data.get('academic_year'),
            class_teacher_id=data.get('class_teacher_id'),
            capacity=data.get('capacity', 40),
        )
        db.session.add(new_class)
        db.session.commit()
        return jsonify({'message': 'Class created', 'id': new_class.id}), 201

    @app.route('/api/classes/<int:id>', methods=['PUT'])
    def update_class(id):
        c = Class.query.get_or_404(id)
        data = request.get_json()

        c.name             = data.get('name',             c.name)
        c.academic_year    = data.get('academic_year',    c.academic_year)
        c.class_teacher_id = data.get('class_teacher_id', c.class_teacher_id)
        c.capacity         = data.get('capacity',         c.capacity)

        db.session.commit()
        return jsonify({'message': 'Class updated'}), 200

    @app.route('/api/classes/<int:id>', methods=['DELETE'])
    def delete_class(id):
        c = Class.query.get_or_404(id)
        db.session.delete(c)
        db.session.commit()
        return jsonify({'message': 'Class deleted'}), 200

    # =========================================================
    #  SUBJECTS
    # =========================================================
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
                'teacher_name': (
                    f"{s.teacher.first_name} {s.teacher.last_name}" if s.teacher else None
                ),
            })
        return jsonify(result), 200

    @app.route('/api/subjects/<int:id>', methods=['GET'])
    def get_subject(id):
        s = Subject.query.get_or_404(id)
        return jsonify({
            'id': s.id,
            'name': s.name,
            'code': s.code,
            'class_id': s.class_id,
            'class_name': s.class_.name if s.class_ else None,
            'teacher_id': s.teacher_id,
            'teacher_name': (
                f"{s.teacher.first_name} {s.teacher.last_name}" if s.teacher else None
            ),
        }), 200

    @app.route('/api/subjects/class/<int:class_id>', methods=['GET'])
    def get_subjects_by_class(class_id):
        subjects = Subject.query.filter_by(class_id=class_id).all()
        return jsonify([{
            'id': s.id,
            'name': s.name,
            'code': s.code,
            'teacher_name': (
                f"{s.teacher.first_name} {s.teacher.last_name}" if s.teacher else None
            ),
        } for s in subjects]), 200

    @app.route('/api/subjects', methods=['POST'])
    def create_subject():
        data = request.get_json()
        if not data.get('name'):
            return jsonify({'message': 'Subject name is required'}), 400

        if data.get('code') and Subject.query.filter_by(code=data['code']).first():
            return jsonify({'message': 'Subject code already exists'}), 409

        subject = Subject(
            name=data['name'],
            code=data.get('code'),
            class_id=data.get('class_id'),
            teacher_id=data.get('teacher_id'),
        )
        db.session.add(subject)
        db.session.commit()
        return jsonify({'message': 'Subject created', 'id': subject.id}), 201

    @app.route('/api/subjects/<int:id>', methods=['PUT'])
    def update_subject(id):
        s = Subject.query.get_or_404(id)
        data = request.get_json()

        s.name       = data.get('name',       s.name)
        s.code       = data.get('code',       s.code)
        s.class_id   = data.get('class_id',   s.class_id)
        s.teacher_id = data.get('teacher_id', s.teacher_id)

        db.session.commit()
        return jsonify({'message': 'Subject updated'}), 200

    @app.route('/api/subjects/<int:id>', methods=['DELETE'])
    def delete_subject(id):
        s = Subject.query.get_or_404(id)
        db.session.delete(s)
        db.session.commit()
        return jsonify({'message': 'Subject deleted'}), 200

    # =========================================================
    #  FEES & PAYMENTS
    # =========================================================
    @app.route('/api/students/<int:student_id>/payments', methods=['GET'])
    def get_student_payments(student_id):
        payments = (Payment.query
                    .join(Fee)
                    .filter(Fee.student_id == student_id)
                    .order_by(Payment.payment_date.desc())
                    .all())
        return jsonify([{
            'id': p.id,
            'amount': p.amount,
            'date': p.payment_date.isoformat(),
            'method': p.payment_method,
            'transaction_id': p.transaction_id,
            'term': p.fee.term,
        } for p in payments]), 200

    @app.route('/api/payments', methods=['POST'])
    def record_payment():
        data = request.get_json()

        student_id = data.get('student_id')
        amount     = data.get('amount')
        term       = data.get('term', 'Term 1 2024')
        method     = data.get('method', 'Cash')
        txn_id     = data.get('transaction_id')

        if not student_id or not amount:
            return jsonify({'message': 'student_id and amount are required'}), 400

        # Find or create fee record for this student + term
        fee = Fee.query.filter_by(student_id=student_id, term=term).first()
        if not fee:
            fee = Fee(
                student_id=student_id,
                term=term,
                total_amount=50000,
                paid_amount=0.0,
                status='pending',
            )
            db.session.add(fee)
            db.session.flush()

        payment = Payment(
            fee_id=fee.id,
            amount=amount,
            payment_method=method,
            transaction_id=txn_id,
            payment_date=datetime.utcnow(),
        )
        db.session.add(payment)

        # Update fee balance and status
        fee.paid_amount += amount
        if fee.paid_amount >= fee.total_amount:
            fee.status = 'paid'
        elif fee.paid_amount > 0:
            fee.status = 'partial'

        db.session.commit()
        return jsonify({
            'message': 'Payment recorded successfully',
            'payment_id': payment.id,
            'fee_status': fee.status,
            'balance': fee.total_amount - fee.paid_amount,
        }), 201

    # =========================================================
    #  STUDENT DASHBOARD
    # =========================================================
    @app.route('/api/student/<int:student_id>/subjects', methods=['GET'])
    def get_student_subjects(student_id):
        student = User.query.filter_by(
            id=student_id, role=UserRole.STUDENT
        ).first_or_404()
        if not student.class_:
            return jsonify([]), 200

        subjects = Subject.query.filter_by(class_id=student.current_class_id).all()
        return jsonify([{
            'id': s.id,
            'name': s.name,
            'code': s.code,
            'teacher_name': (
                f"{s.teacher.first_name} {s.teacher.last_name}" if s.teacher else None
            ),
            'coursework_count': Coursework.query.filter_by(subject_id=s.id).count(),
        } for s in subjects]), 200

    @app.route('/api/student/<int:student_id>/fees', methods=['GET'])
    def get_student_fees(student_id):
        fees = Fee.query.filter_by(student_id=student_id).all()
        total_balance = 0
        fee_list = []
        for f in fees:
            balance = f.total_amount - f.paid_amount
            total_balance += balance
            fee_list.append({
                'id': f.id,
                'term': f.term,
                'total_amount': f.total_amount,
                'paid_amount': f.paid_amount,
                'balance': balance,
                'status': f.status,
                'due_date': f.due_date.isoformat() if f.due_date else None,
            })

        payments = (Payment.query
                    .join(Fee)
                    .filter(Fee.student_id == student_id)
                    .order_by(Payment.payment_date.desc())
                    .all())

        return jsonify({
            'fees': fee_list,
            'total_balance': total_balance,
            'payment_history': [{
                'amount': p.amount,
                'date': p.payment_date.isoformat(),
                'method': p.payment_method,
                'transaction_id': p.transaction_id,
            } for p in payments],
        }), 200

    @app.route('/api/student/<int:student_id>/attendance', methods=['GET'])
    def get_student_attendance(student_id):
        records = (Attendance.query
                   .filter_by(student_id=student_id)
                   .order_by(Attendance.date.desc())
                   .all())

        present = sum(1 for a in records if a.status == AttendanceStatus.PRESENT)
        absent  = sum(1 for a in records if a.status == AttendanceStatus.ABSENT)
        late    = sum(1 for a in records if a.status == AttendanceStatus.LATE)
        total   = len(records)
        pct     = round(present / total * 100, 2) if total > 0 else 0

        return jsonify({
            'records': [{
                'date': a.date.isoformat(),
                'status': a.status.value,
                'remarks': a.remarks,
            } for a in records],
            'percentage': pct,
            'present': present,
            'absent': absent,
            'late': late,
            'total': total,
        }), 200

    @app.route('/api/student/<int:student_id>/courseworks', methods=['GET'])
    def get_student_courseworks(student_id):
        student = User.query.filter_by(
            id=student_id, role=UserRole.STUDENT
        ).first_or_404()
        if not student.class_:
            return jsonify([]), 200

        subject_ids = [s.id for s in
                       Subject.query.filter_by(class_id=student.current_class_id).all()]
        courseworks = (Coursework.query
                       .filter(Coursework.subject_id.in_(subject_ids))
                       .order_by(Coursework.due_date)
                       .all())

        result = []
        for c in courseworks:
            sub = Submission.query.filter_by(
                coursework_id=c.id, student_id=student_id
            ).first()
            result.append({
                'id': c.id,
                'title': c.title,
                'description': c.description,
                'type': c.type.value,
                'subject_name': c.subject.name,
                'teacher_name': f"{c.teacher.first_name} {c.teacher.last_name}",
                'due_date': c.due_date.isoformat() if c.due_date else None,
                'total_marks': c.total_marks,
                'submitted': sub is not None,
                'submission_id': sub.id if sub else None,
                'marks_obtained': sub.marks_obtained if sub else None,
                'feedback': sub.feedback if sub else None,
                'status': sub.status.value if sub else 'pending',
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
            status=SubmissionStatus.SUBMITTED,
        )
        db.session.add(submission)
        db.session.commit()
        return jsonify({'message': 'Submitted successfully', 'id': submission.id}), 201

    # =========================================================
    #  TEACHER DASHBOARD
    # =========================================================
    @app.route('/api/teacher/<int:teacher_id>/subjects', methods=['GET'])
    def get_teacher_subjects(teacher_id):
        subjects = Subject.query.filter_by(teacher_id=teacher_id).all()
        return jsonify([{
            'id': s.id,
            'name': s.name,
            'code': s.code,
            'class_name': s.class_.name if s.class_ else None,
            'student_count': User.query.filter_by(
                role=UserRole.STUDENT, current_class_id=s.class_id
            ).count(),
        } for s in subjects]), 200

    @app.route('/api/teacher/<int:teacher_id>/courseworks', methods=['GET'])
    def get_teacher_courseworks(teacher_id):
        courseworks = (Coursework.query
                       .filter_by(teacher_id=teacher_id)
                       .order_by(Coursework.created_at.desc())
                       .all())
        result = []
        for c in courseworks:
            submissions = Submission.query.filter_by(coursework_id=c.id).all()
            graded = sum(1 for s in submissions if s.marks_obtained is not None)
            result.append({
                'id': c.id,
                'title': c.title,
                'description': c.description,
                'type': c.type.value,
                'subject_name': c.subject.name,
                'class_name': c.subject.class_.name if c.subject.class_ else None,
                'due_date': c.due_date.isoformat() if c.due_date else None,
                'total_marks': c.total_marks,
                'submissions': len(submissions),
                'graded': graded,
            })
        return jsonify(result), 200

    @app.route('/api/create-coursework', methods=['POST'])
    def create_coursework():
        data = request.get_json()
        try:
            cw_type = CourseworkType[data['type'].upper()]
        except KeyError:
            return jsonify({'message': f"Invalid type. Use: {[e.name for e in CourseworkType]}"}), 400

        coursework = Coursework(
            subject_id=data['subject_id'],
            teacher_id=data['teacher_id'],
            title=data['title'],
            description=data.get('description'),
            type=cw_type,
            due_date=(datetime.fromisoformat(data['due_date'])
                      if data.get('due_date') else None),
            total_marks=data.get('total_marks'),
        )
        db.session.add(coursework)
        db.session.commit()
        return jsonify({'message': 'Coursework created', 'id': coursework.id}), 201

    @app.route('/api/teacher/<int:teacher_id>/timetable', methods=['GET'])
    def get_teacher_timetable(teacher_id):
        subject_ids = [s.id for s in
                       Subject.query.filter_by(teacher_id=teacher_id).all()]
        timetable = TimetableEntry.query.filter(
            TimetableEntry.subject_id.in_(subject_ids)
        ).all()
        return jsonify([{
            'id': t.id,
            'day': t.day_of_week,
            'start': t.start_time.isoformat() if t.start_time else None,
            'end': t.end_time.isoformat() if t.end_time else None,
            'subject': t.subject.name,
            'class': t.class_.name,
            'room': t.room,
        } for t in timetable]), 200

    @app.route('/api/teacher/<int:teacher_id>/submissions/<int:coursework_id>',
               methods=['GET'])
    def get_submissions_for_grading(teacher_id, coursework_id):
        Coursework.query.filter_by(
            id=coursework_id, teacher_id=teacher_id
        ).first_or_404()
        submissions = Submission.query.filter_by(coursework_id=coursework_id).all()
        return jsonify([{
            'id': s.id,
            'student_name': f"{s.student.first_name} {s.student.last_name}",
            'admission': s.student.admission_number,
            'submission_date': s.submission_date.isoformat(),
            'content': s.content,
            'file_path': s.file_path,
            'marks_obtained': s.marks_obtained,
            'feedback': s.feedback,
            'status': s.status.value,
        } for s in submissions]), 200

    @app.route('/api/grade-submission', methods=['POST'])
    def grade_submission():
        data = request.get_json()
        submission = Submission.query.get_or_404(data['submission_id'])
        submission.marks_obtained = data['marks_obtained']
        submission.feedback       = data.get('feedback')
        submission.status         = SubmissionStatus.GRADED
        db.session.commit()
        return jsonify({'message': 'Submission graded successfully'}), 200

    # =========================================================
    #  PARENT DASHBOARD
    # =========================================================
    @app.route('/api/parent/<int:parent_id>/children', methods=['GET'])
    def get_parent_children(parent_id):
        parent = User.query.filter_by(
            id=parent_id, role=UserRole.PARENT
        ).first_or_404()

        result = []
        for child in parent.children:
            # Attendance stats
            att_records = Attendance.query.filter_by(student_id=child.id).all()
            present = sum(1 for a in att_records
                          if a.status == AttendanceStatus.PRESENT)
            total_att = len(att_records)
            att_pct = round(present / total_att * 100, 2) if total_att > 0 else 0

            # Fee balance
            fees = Fee.query.filter_by(student_id=child.id).all()
            fee_balance = sum(f.total_amount - f.paid_amount for f in fees)

            # Grades from exam results
            grades = []
            for er in ExamResult.query.filter_by(student_id=child.id).all():
                grades.append({
                    'exam': er.exam.name,
                    'subject': er.exam.subject.name,
                    'marks': er.marks_obtained,
                    'grade': er.grade,
                })

            # Coursework submissions
            courseworks = []
            for sub in Submission.query.filter_by(student_id=child.id).all():
                courseworks.append({
                    'title': sub.coursework.title,
                    'subject': sub.coursework.subject.name,
                    'marks': sub.marks_obtained,
                    'feedback': sub.feedback,
                    'status': sub.status.value,
                })

            result.append({
                'id': child.id,
                'name': f"{child.first_name} {child.last_name}",
                'first_name': child.first_name,
                'last_name': child.last_name,
                'admission': child.admission_number,
                'admission_number': child.admission_number,
                'class': child.class_.name if child.class_ else None,
                'class_name': child.class_.name if child.class_ else None,
                'gender': child.gender.value if child.gender else None,
                'attendance_percentage': att_pct,
                'fee_balance': fee_balance,
                'grades': grades,
                'courseworks': courseworks,
            })
        return jsonify(result), 200

    # =========================================================
    #  DASHBOARD STATS
    # =========================================================
    @app.route('/api/dashboard/stats', methods=['GET'])
    def get_dashboard_stats():
        return jsonify({
            'totalStudents': User.query.filter_by(role=UserRole.STUDENT).count(),
            'totalTeachers': User.query.filter_by(role=UserRole.TEACHER).count(),
            'totalClasses':  Class.query.count(),
            'totalSubjects': Subject.query.count(),
            'todayAttendance': '85%',
        }), 200

    @app.route('/api/dashboard/recent-students', methods=['GET'])
    def get_recent_students():
        students = (User.query
                    .filter_by(role=UserRole.STUDENT)
                    .order_by(User.id.desc())
                    .limit(5).all())
        return jsonify([{
            'id': s.id,
            'name': f"{s.first_name} {s.last_name}",
            'admission_number': s.admission_number,
        } for s in students]), 200

    @app.route('/api/dashboard/upcoming-exams', methods=['GET'])
    def get_upcoming_exams():
        exams = Exam.query.order_by(Exam.exam_date).limit(5).all()
        return jsonify([{
            'name': e.name,
            'date': e.exam_date.isoformat() if e.exam_date else None,
            'subject': e.subject.name,
        } for e in exams]), 200

    @app.route('/api/dashboard/pending-fees', methods=['GET'])
    def get_pending_fees():
        fees = Fee.query.filter(Fee.status != 'paid').limit(5).all()
        return jsonify([{
            'student_name': (
                f"{User.query.get(f.student_id).first_name} "
                f"{User.query.get(f.student_id).last_name}"
            ) if User.query.get(f.student_id) else 'Unknown',
            'balance': f.total_amount - f.paid_amount,
            'term': f.term,
        } for f in fees]), 200

    # =========================================================
    #  ANNOUNCEMENTS
    # =========================================================
    @app.route('/api/announcements', methods=['GET'])
    def get_announcements():
        role_filter = request.args.get('role')
        query = Announcement.query
        if role_filter:
            try:
                role_enum = UserRole[role_filter.upper()]
                query = query.filter(
                    (Announcement.target_role == role_enum) |
                    (Announcement.target_role == None)
                )
            except KeyError:
                pass
        announcements = query.order_by(Announcement.created_at.desc()).all()
        return jsonify([{
            'id': a.id,
            'title': a.title,
            'content': a.content,
            'target_role': a.target_role.value if a.target_role else 'All',
            'created_at': a.created_at.isoformat(),
            'expires_at': a.expires_at.isoformat() if a.expires_at else None,
        } for a in announcements]), 200

    @app.route('/api/announcements', methods=['POST'])
    def create_announcement():
        data = request.get_json()
        if not data.get('title') or not data.get('content'):
            return jsonify({'message': 'title and content are required'}), 400

        target_role = None
        if data.get('target_role') and data['target_role'] != 'All':
            try:
                target_role = UserRole[data['target_role'].upper()]
            except KeyError:
                pass

        ann = Announcement(
            title=data['title'],
            content=data['content'],
            target_role=target_role,
            created_by=data.get('created_by'),
            created_at=datetime.utcnow(),
        )
        db.session.add(ann)
        db.session.commit()
        return jsonify({'message': 'Announcement created', 'id': ann.id}), 201

    return app