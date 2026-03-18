from app.database import db
from datetime import date, datetime
from sqlalchemy import Enum as SQLEnum
import enum

# ----- Enums for consistent choices -----
class UserRole(enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"

class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class AttendanceStatus(enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"

class CourseworkType(enum.Enum):
    ASSIGNMENT = "assignment"
    CAT = "cat"
    EXAM = "exam"

class SubmissionStatus(enum.Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    LATE = "late"
    GRADED = "graded"

# ----- Association Tables (many-to-many) -----
student_parent = db.Table(
    'student_parent',
    db.Column('student_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('parent_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

# ----- User Model (Single table for all users) -----
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(SQLEnum(UserRole), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    gender = db.Column(SQLEnum(Gender))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Role-specific fields (all nullable)
    # Student fields
    admission_number = db.Column(db.String(20), unique=True, nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    enrollment_date = db.Column(db.Date, nullable=True)
    current_class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=True)
    
    # Teacher fields
    employee_id = db.Column(db.String(20), unique=True, nullable=True)
    qualification = db.Column(db.String(100), nullable=True)
    hire_date = db.Column(db.Date, nullable=True)
    
    # Admin fields
    department = db.Column(db.String(100), nullable=True)
    
    # Parent fields
    occupation = db.Column(db.String(100), nullable=True)
    
    # Relationships
    
    # As student - class relationship
    class_ = db.relationship('Class', foreign_keys=[current_class_id], back_populates='students')
    
    # Attendance relationships
    attendances = db.relationship('Attendance', 
                                  foreign_keys='Attendance.student_id',
                                  back_populates='student', 
                                  lazy=True)
    
    attendance_records = db.relationship('Attendance',
                                         foreign_keys='Attendance.recorded_by',
                                         back_populates='recorder',
                                         lazy=True)
    
    # Exam results
    exam_results = db.relationship('ExamResult', 
                                   foreign_keys='ExamResult.student_id',
                                   back_populates='student', 
                                   lazy=True)
    
    # Fee records
    fee_records = db.relationship('Fee', 
                                  foreign_keys='Fee.student_id',
                                  back_populates='student', 
                                  lazy=True)
    
    # As parent - children relationship
    children = db.relationship('User', 
                               secondary=student_parent,
                               primaryjoin=id == student_parent.c.parent_id,
                               secondaryjoin=id == student_parent.c.student_id,
                               back_populates='parents')
    
    # As child - parents relationship
    parents = db.relationship('User',
                              secondary=student_parent,
                              primaryjoin=id == student_parent.c.student_id,
                              secondaryjoin=id == student_parent.c.parent_id,
                              back_populates='children')
    
    # As teacher - subjects taught
    subjects_taught = db.relationship('Subject', 
                                      foreign_keys='Subject.teacher_id',
                                      back_populates='teacher', 
                                      lazy=True)
    
    # Coursework created by teacher
    courseworks_created = db.relationship('Coursework',
                                         foreign_keys='Coursework.teacher_id',
                                         back_populates='teacher',
                                         lazy=True)
    
    # Submissions by student
    submissions = db.relationship('Submission',
                                  foreign_keys='Submission.student_id',
                                  back_populates='student',
                                  lazy=True)
    
    # As class teacher
    class_teacher = db.relationship('Class',
                                    foreign_keys='Class.class_teacher_id',
                                    back_populates='class_teacher',
                                    lazy=True)
    
    # Payments received (as admin/teacher)
    payments_received = db.relationship('Payment',
                                        foreign_keys='Payment.received_by',
                                        back_populates='receiver',
                                        lazy=True)
    
    # Announcements created
    announcements_created = db.relationship('Announcement',
                                           foreign_keys='Announcement.created_by',
                                           back_populates='creator',
                                           lazy=True)

# ----- Academic Structure -----
class Class(db.Model):
    __tablename__ = 'class'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    academic_year = db.Column(db.String(9))
    class_teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    capacity = db.Column(db.Integer)
    
    # Relationships
    class_teacher = db.relationship('User', foreign_keys=[class_teacher_id], back_populates='class_teacher')
    students = db.relationship('User', foreign_keys='User.current_class_id', back_populates='class_')
    subjects = db.relationship('Subject', back_populates='class_', lazy=True)
    timetable_entries = db.relationship('TimetableEntry', back_populates='class_', lazy=True)

class Subject(db.Model):
    __tablename__ = 'subject'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), unique=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'))
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    class_ = db.relationship('Class', back_populates='subjects')
    teacher = db.relationship('User', foreign_keys=[teacher_id], back_populates='subjects_taught')
    exams = db.relationship('Exam', back_populates='subject', lazy=True)
    courseworks = db.relationship('Coursework', back_populates='subject', lazy=True)
    timetable_entries = db.relationship('TimetableEntry', back_populates='subject', lazy=True)

# ----- Coursework and Submissions (NEW) -----
class Coursework(db.Model):
    __tablename__ = 'coursework'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(SQLEnum(CourseworkType), nullable=False)
    due_date = db.Column(db.DateTime)
    total_marks = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    subject = db.relationship('Subject', back_populates='courseworks')
    teacher = db.relationship('User', foreign_keys=[teacher_id], back_populates='courseworks_created')
    submissions = db.relationship('Submission', back_populates='coursework', lazy=True, cascade='all, delete-orphan')

class Submission(db.Model):
    __tablename__ = 'submission'
    id = db.Column(db.Integer, primary_key=True)
    coursework_id = db.Column(db.Integer, db.ForeignKey('coursework.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    submission_date = db.Column(db.DateTime, default=datetime.utcnow)
    file_path = db.Column(db.String(500))
    content = db.Column(db.Text)
    marks_obtained = db.Column(db.Float)
    feedback = db.Column(db.Text)
    status = db.Column(SQLEnum(SubmissionStatus), default='SUBMITTED')
    
    # Relationships
    coursework = db.relationship('Coursework', back_populates='submissions')
    student = db.relationship('User', foreign_keys=[student_id], back_populates='submissions')

# ----- Attendance -----
class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=date.today, nullable=False)
    status = db.Column(SQLEnum(AttendanceStatus), nullable=False)
    remarks = db.Column(db.String(200))
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships with explicit foreign keys
    student = db.relationship('User', 
                             foreign_keys=[student_id],
                             back_populates='attendances')
    recorder = db.relationship('User',
                              foreign_keys=[recorded_by],
                              back_populates='attendance_records')

# ----- Exams & Results -----
class Exam(db.Model):
    __tablename__ = 'exam'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    exam_date = db.Column(db.Date)
    total_marks = db.Column(db.Float)
    pass_mark = db.Column(db.Float)
    
    # Relationships
    subject = db.relationship('Subject', back_populates='exams')
    results = db.relationship('ExamResult', back_populates='exam', lazy=True, cascade='all, delete-orphan')

class ExamResult(db.Model):
    __tablename__ = 'exam_result'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    marks_obtained = db.Column(db.Float)
    grade = db.Column(db.String(2))
    remarks = db.Column(db.String(200))
    
    # Relationships with explicit foreign keys
    exam = db.relationship('Exam', back_populates='results')
    student = db.relationship('User', 
                             foreign_keys=[student_id],
                             back_populates='exam_results')

# ----- Fees & Payments -----
class Fee(db.Model):
    __tablename__ = 'fee'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    term = db.Column(db.String(20))
    total_amount = db.Column(db.Float, nullable=False)
    paid_amount = db.Column(db.Float, default=0.0)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='pending')
    
    # Relationships with explicit foreign keys
    student = db.relationship('User', 
                             foreign_keys=[student_id],
                             back_populates='fee_records')
    payments = db.relationship('Payment', back_populates='fee', lazy=True, cascade='all, delete-orphan')

class Payment(db.Model):
    __tablename__ = 'payment'
    id = db.Column(db.Integer, primary_key=True)
    fee_id = db.Column(db.Integer, db.ForeignKey('fee.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_method = db.Column(db.String(50))
    transaction_id = db.Column(db.String(100), unique=True)
    received_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships with explicit foreign keys
    fee = db.relationship('Fee', back_populates='payments')
    receiver = db.relationship('User',
                              foreign_keys=[received_by],
                              back_populates='payments_received')

# ----- Communication -----
class Announcement(db.Model):
    __tablename__ = 'announcement'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    target_role = db.Column(SQLEnum(UserRole))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    
    # Relationships with explicit foreign keys
    creator = db.relationship('User',
                             foreign_keys=[created_by],
                             back_populates='announcements_created')

# ----- Timetable -----
class TimetableEntry(db.Model):
    __tablename__ = 'timetable_entry'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    day_of_week = db.Column(db.String(10))
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    room = db.Column(db.String(20))
    
    # Relationships
    class_ = db.relationship('Class', back_populates='timetable_entries')
    subject = db.relationship('Subject', back_populates='timetable_entries')