import os
import sqlite3
from datetime import datetime
from flask import (
    Flask, g, request, session,
    jsonify, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


app = Flask(__name__, static_folder='static', static_url_path='')
app.secret_key = 'smartlearn-secret-key-change-in-production'


DATABASE      = 'smartlearn.db'
print("DB PATH:", os.path.abspath(DATABASE))
UPLOAD_VIDEOS = os.path.join('uploads', 'videos')
UPLOAD_NOTES  = os.path.join('uploads', 'notes')
UPLOAD_PAPERS = os.path.join('uploads', 'papers')

os.makedirs(UPLOAD_VIDEOS, exist_ok=True)
os.makedirs(UPLOAD_NOTES,  exist_ok=True)
os.makedirs(UPLOAD_PAPERS, exist_ok=True)

ALLOWED_VIDEO = {'mp4', 'webm', 'mkv'}
ALLOWED_NOTES = {'pdf', 'doc', 'docx', 'ppt', 'pptx'}
ALLOWED_PAPER = {'pdf'}


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        with open('schema.sql', 'r') as f:
            db.executescript(f.read())
        db.commit()


def seed_data():
    db = get_db()
    subjects = [
        ('Mathematics','math'),('Science','science'),
        ('English','english'),('Social Studies','social'),
        ('Computer Science','computer')
    ]
    for name, slug in subjects:
        db.execute('INSERT OR IGNORE INTO subjects (name,slug) VALUES (?,?)',(name,slug))
    teacher_pw = generate_password_hash('teacher123')
    db.execute(
        'INSERT OR IGNORE INTO users (name,username,password_hash,role,staff_id) VALUES (?,?,?,?,?)',
        ('Teacher','teacher',teacher_pw,'teacher','STAFF001')
    )
    db.commit()


def is_logged_in(): return 'user_id' in session
def is_teacher():   return is_logged_in() and session.get('role')=='teacher'
def is_student():   return is_logged_in() and session.get('role')=='student'


def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in allowed_set


# ─────────────────────────────────────────────────────────────────────────────
# STATIC FILES
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

@app.get('/uploads/videos/<filename>')
def serve_video(filename):
    return send_from_directory(UPLOAD_VIDEOS, filename)

@app.get('/uploads/notes/<filename>')
def serve_notes(filename):
    return send_from_directory(UPLOAD_NOTES, filename)

@app.get('/uploads/papers/<filename>')
def serve_paper(filename):
    return send_from_directory(UPLOAD_PAPERS, filename)


# ─────────────────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────────────────

@app.post('/api/login')
def login():
    data     = request.get_json()
    role     = data.get('role','').strip()
    password = data.get('password','').strip()

    if role == 'student':
        name      = data.get('name','').strip()
        class_div = data.get('class_div','').strip()
        roll      = data.get('roll','').strip()
        if not name or not roll:
            return jsonify({'success':False,'message':'Name and roll number required'}),400
        db   = get_db()
        user = db.execute('SELECT * FROM users WHERE roll=? AND role=?',(roll,'student')).fetchone()
        if not user:
            pw_hash = generate_password_hash(roll)
            cur = db.execute(
                'INSERT INTO users (name,username,password_hash,role,class_div,roll) VALUES (?,?,?,?,?,?)',
                (name,roll,pw_hash,'student',class_div,roll)
            )
            db.commit()
            user_id   = cur.lastrowid
            user_name = name
        else:
            user_id   = user['id']
            user_name = user['name']
        session.update({'user_id':user_id,'role':'student','name':user_name,'class_div':class_div,'roll':roll})
        return jsonify({'success':True,'role':'student','name':user_name})

    elif role == 'teacher':
        staff_id = data.get('staff_id','').strip()
        if not staff_id or not password:
            return jsonify({'success':False,'message':'Staff ID and password required'}),400
        db   = get_db()
        user = db.execute('SELECT * FROM users WHERE staff_id=? AND role=?',(staff_id,'teacher')).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session.update({'user_id':user['id'],'role':'teacher','name':user['name']})
            return jsonify({'success':True,'role':'teacher','name':user['name']})
        all_teachers = db.execute('SELECT * FROM users WHERE role=?',('teacher',)).fetchall()
        for u in all_teachers:
            if check_password_hash(u['password_hash'], password):
                session.update({'user_id':u['id'],'role':'teacher','name':u['name']})
                return jsonify({'success':True,'role':'teacher','name':u['name']})
        return jsonify({'success':False,'message':'Invalid Staff ID or PIN'}),401

@app.get('/api/logout')
def logout():
    session.clear()
    return jsonify({'success':True})


@app.get('/api/me')
def me():
    if not is_logged_in(): return jsonify({'loggedIn':False})
    return jsonify({'loggedIn':True,'user_id':session['user_id'],'role':session['role'],'name':session['name']})


# ─────────────────────────────────────────────────────────────────────────────
# SUBJECTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get('/api/subjects')
def get_subjects():
    rows = get_db().execute('SELECT * FROM subjects ORDER BY name').fetchall()
    return jsonify([dict(r) for r in rows])


# ─────────────────────────────────────────────────────────────────────────────
# CHAPTERS
# ─────────────────────────────────────────────────────────────────────────────

@app.post('/api/chapters')
def create_chapter():
    if not is_teacher(): return jsonify({'success':False,'message':'Unauthorized'}),403
    title        = request.form.get('title','').strip()
    description  = request.form.get('description','').strip()
    subject_slug = request.form.get('subject','').strip()
    if not title or not subject_slug:
        return jsonify({'success':False,'message':'Title and subject required'}),400
    db      = get_db()
    subject = db.execute('SELECT * FROM subjects WHERE slug=?',(subject_slug,)).fetchone()
    if not subject: return jsonify({'success':False,'message':'Invalid subject'}),400
    cur = db.execute(
        'INSERT INTO chapters (subject_id,title,description,created_by) VALUES (?,?,?,?)',
        (subject['id'],title,description,session['user_id'])
    )
    db.commit()
    return jsonify({'success':True,'chapter_id':cur.lastrowid})


@app.get('/api/subjects/<subject_slug>/chapters')
def get_chapters(subject_slug):
    db      = get_db()
    subject = db.execute('SELECT * FROM subjects WHERE slug=?',(subject_slug,)).fetchone()
    if not subject: return jsonify([])
    chapters = db.execute('SELECT * FROM chapters WHERE subject_id=? ORDER BY id',(subject['id'],)).fetchall()
    output = []
    for ch in chapters:
        files   = db.execute('SELECT * FROM files WHERE chapter_id=?',(ch['id'],)).fetchall()
        quizzes = db.execute('SELECT * FROM quizzes WHERE chapter_id=?',(ch['id'],)).fetchall()
        quiz_list = []
        for qz in quizzes:
            qs = db.execute('SELECT * FROM questions WHERE quiz_id=?',(qz['id'],)).fetchall()
            quiz_list.append({'id':qz['id'],'title':qz['title'],'questions':[
                {'q':q['question'],'options':[q['option1'],q['option2'],q['option3'],q['option4']],'correct':q['correct_index']}
                for q in qs]})
        file_list = [{'id':f['id'],'name':f['original_name'],'type':f['file_type'],
                      'url':f'/uploads/{"videos" if f["file_type"]=="video" else "notes"}/{f["stored_name"]}'}
                     for f in files]
        output.append({'id':ch['id'],'title':ch['title'],'description':ch['description'] or '',
                       'files':file_list,'quizzes':quiz_list})
    return jsonify(output)


@app.delete('/api/chapters/<int:chapter_id>')
def delete_chapter(chapter_id):
    if not is_teacher(): return jsonify({'success':False,'message':'Unauthorized'}),403
    db = get_db()
    db.execute('DELETE FROM files WHERE chapter_id=?',(chapter_id,))
    db.execute('DELETE FROM results WHERE quiz_id IN (SELECT id FROM quizzes WHERE chapter_id=?)',(chapter_id,))
    db.execute('DELETE FROM questions WHERE quiz_id IN (SELECT id FROM quizzes WHERE chapter_id=?)',(chapter_id,))
    db.execute('DELETE FROM quizzes WHERE chapter_id=?',(chapter_id,))
    db.execute('DELETE FROM chapters WHERE id=?',(chapter_id,))
    db.commit()
    return jsonify({'success':True})


# ─────────────────────────────────────────────────────────────────────────────
# FILE UPLOADS (VIDEO / NOTES)
# ─────────────────────────────────────────────────────────────────────────────

@app.post('/api/upload')
def upload_file():
    if not is_teacher(): return jsonify({'success':False,'message':'Unauthorized'}),403
    chapter_id = request.form.get('chapter_id')
    file_type  = request.form.get('file_type')
    file       = request.files.get('file')
    if not chapter_id or not file_type or not file:
        return jsonify({'success':False,'message':'Missing data'}),400
    if file_type=='video' and not allowed_file(file.filename, ALLOWED_VIDEO):
        return jsonify({'success':False,'message':'Only MP4/WEBM allowed'}),400
    if file_type=='notes' and not allowed_file(file.filename, ALLOWED_NOTES):
        return jsonify({'success':False,'message':'Only PDF/DOC/PPT allowed'}),400
    filename    = secure_filename(file.filename)
    stored_name = f"{chapter_id}_{filename}"
    folder      = UPLOAD_VIDEOS if file_type=='video' else UPLOAD_NOTES
    file.save(os.path.join(folder, stored_name))
    db  = get_db()
    cur = db.execute('INSERT INTO files (chapter_id,file_type,original_name,stored_name) VALUES (?,?,?,?)',
                     (chapter_id,file_type,filename,stored_name))
    db.commit()
    url = f'/uploads/{"videos" if file_type=="video" else "notes"}/{stored_name}'
    return jsonify({'success':True,'file_id':cur.lastrowid,'url':url,'name':filename})


@app.delete('/api/files/<int:file_id>')
def delete_file(file_id):
    if not is_teacher(): return jsonify({'success':False,'message':'Unauthorized'}),403
    db  = get_db()
    row = db.execute('SELECT * FROM files WHERE id=?',(file_id,)).fetchone()
    if not row: return jsonify({'success':False,'message':'Not found'}),404
    path = os.path.join(UPLOAD_VIDEOS if row['file_type']=='video' else UPLOAD_NOTES, row['stored_name'])
    if os.path.exists(path): os.remove(path)
    db.execute('DELETE FROM files WHERE id=?',(file_id,))
    db.commit()
    return jsonify({'success':True})


# ─────────────────────────────────────────────────────────────────────────────
# QUIZZES
# ─────────────────────────────────────────────────────────────────────────────

@app.post('/api/quizzes')
def create_quiz():
    if not is_teacher(): return jsonify({'success':False,'message':'Unauthorized'}),403
    data       = request.get_json()
    chapter_id = data.get('chapter_id')
    title      = data.get('title','').strip()
    questions  = data.get('questions',[])
    if not chapter_id or not title or not questions:
        return jsonify({'success':False,'message':'Missing data'}),400
    db  = get_db()
    cur = db.execute('INSERT INTO quizzes (chapter_id,title) VALUES (?,?)',(chapter_id,title))
    quiz_id = cur.lastrowid
    for q in questions:
        opts = q.get('options','['''''''']')
        while len(opts)<4: opts.append('')
        db.execute(
            'INSERT INTO questions (quiz_id,question,option1,option2,option3,option4,correct_index) VALUES (?,?,?,?,?,?,?)',
            (quiz_id,q['q'],opts[0],opts[1],opts[2],opts[3],q['correct'])
        )
    db.commit()
    return jsonify({'success':True,'quiz_id':quiz_id})


@app.delete('/api/quizzes/<int:quiz_id>')
def delete_quiz(quiz_id):
    if not is_teacher(): return jsonify({'success':False,'message':'Unauthorized'}),403
    db = get_db()
    db.execute('DELETE FROM questions WHERE quiz_id=?',(quiz_id,))
    db.execute('DELETE FROM quizzes WHERE id=?',(quiz_id,))
    db.commit()
    return jsonify({'success':True})


# ─────────────────────────────────────────────────────────────────────────────
# QUIZ RESULTS  ← UPDATED: saves from student, reads for teacher
# ─────────────────────────────────────────────────────────────────────────────

@app.post('/api/results')
def save_result():
    data    = request.get_json()
    quiz_id = data.get('quiz_id')
    marks   = data.get('marks')
    total   = data.get('total')

    # Works whether Flask session exists or student uses sessionStorage only
    if is_student():
        student_id = session['user_id']
    else:
        roll = data.get('roll','').strip()
        name = data.get('student','').strip()
        if not roll:
            return jsonify({'success':False,'message':'Roll number required'}),400
        db   = get_db()
        user = db.execute('SELECT id FROM users WHERE roll=? AND role=?',(roll,'student')).fetchone()
        if user:
            student_id = user['id']
        else:
            pw_hash = generate_password_hash(roll)
            cur = db.execute(
                'INSERT INTO users (name,username,password_hash,role,roll) VALUES (?,?,?,?,?)',
                (name or roll,roll,pw_hash,'student',roll)
            )
            db.commit()
            student_id = cur.lastrowid

    if quiz_id is None or marks is None or total is None:
        return jsonify({'success':False,'message':'Missing data'}),400

    db = get_db()
    db.execute(
        'INSERT INTO results (student_id,quiz_id,subject,chapter_title,marks,total,submitted_at) VALUES (?,?,?,?,?,?,?)',
        (student_id, quiz_id,
         data.get('subject',''),
         data.get('chapter_title', data.get('chapter','')),
         marks, total,
         datetime.now().strftime('%d/%m/%Y'))
    )
    db.commit()
    return jsonify({'success':True})


@app.get('/api/results')
def get_results():
    if not is_teacher(): return jsonify({'success':False,'message':'Unauthorized'}),403
    subject = request.args.get('subject','')
    db      = get_db()
    base_q  = """
        SELECT r.id,
               u.name         AS student,
               u.roll,
               r.subject,
               r.chapter_title,
               r.marks,
               r.total,
               r.submitted_at,
               qz.title       AS quiz_title
        FROM   results  r
        JOIN   users    u  ON u.id  = r.student_id
        JOIN   quizzes  qz ON qz.id = r.quiz_id
    """
    if subject:
        rows = db.execute(base_q+' WHERE r.subject=? ORDER BY r.submitted_at DESC',(subject,)).fetchall()
    else:
        rows = db.execute(base_q+' ORDER BY r.submitted_at DESC').fetchall()
    return jsonify([dict(r) for r in rows])


# Summary stats for teacher dashboard cards
@app.get('/api/results/summary')
def results_summary():
    if not is_teacher(): return jsonify({'success':False,'message':'Unauthorized'}),403
    db  = get_db()
    row = db.execute(
        'SELECT COUNT(*) as total, ROUND(AVG(CAST(marks AS REAL)/total*100),1) as avg_pct FROM results'
    ).fetchone()
    return jsonify({'total_attempts':row['total'],'avg_score_pct':row['avg_pct'] or 0})


# ─────────────────────────────────────────────────────────────────────────────
# QUESTION PAPERS
# ─────────────────────────────────────────────────────────────────────────────

@app.post('/api/papers')
def upload_paper():
    if not is_teacher(): return jsonify({'success':False,'message':'Unauthorized'}),403
    subject_slug = request.form.get('subject','').strip()
    title        = request.form.get('title','').strip()
    file         = request.files.get('file')
    if not subject_slug or not title or not file:
        return jsonify({'success':False,'message':'Missing data'}),400
    if not allowed_file(file.filename, ALLOWED_PAPER):
        return jsonify({'success':False,'message':'Only PDF allowed'}),400
    db      = get_db()
    subject = db.execute('SELECT * FROM subjects WHERE slug=?',(subject_slug,)).fetchone()
    if not subject: return jsonify({'success':False,'message':'Invalid subject'}),400
    filename    = secure_filename(file.filename)
    stored_name = f"paper_{subject_slug}_{filename}"
    file.save(os.path.join(UPLOAD_PAPERS, stored_name))
    db.execute('INSERT INTO papers (subject_id,title,stored_name,original_name) VALUES (?,?,?,?)',
               (subject['id'],title,stored_name,filename))
    db.commit()
    return jsonify({'success':True})


@app.get('/api/papers')
def get_papers():
    subject_slug = request.args.get('subject','')
    db           = get_db()
    if subject_slug:
        subject = db.execute('SELECT * FROM subjects WHERE slug=?',(subject_slug,)).fetchone()
        if not subject: return jsonify([])
        rows = db.execute('SELECT * FROM papers WHERE subject_id=? ORDER BY id DESC',(subject['id'],)).fetchall()
    else:
        rows = db.execute('SELECT * FROM papers ORDER BY id DESC').fetchall()
    return jsonify([{'id':r['id'],'title':r['title'],'url':f'/uploads/papers/{r["stored_name"]}'}
                    for r in rows])


@app.delete('/api/papers/<int:paper_id>')
def delete_paper(paper_id):
    if not is_teacher(): return jsonify({'success':False,'message':'Unauthorized'}),403
    db  = get_db()
    row = db.execute('SELECT * FROM papers WHERE id=?',(paper_id,)).fetchone()
    if not row: return jsonify({'success':False,'message':'Not found'}),404
    path = os.path.join(UPLOAD_PAPERS, row['stored_name'])
    if os.path.exists(path): os.remove(path)
    db.execute('DELETE FROM papers WHERE id=?',(paper_id,))
    db.commit()
    return jsonify({'success':True})


# ─────────────────────────────────────────────────────────────────────────────
# STUDENTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get('/api/students')
def get_students():
    if not is_teacher(): return jsonify({'success':False,'message':'Unauthorized'}),403
    rows = get_db().execute(
        'SELECT id,name,roll,class_div FROM users WHERE role=? ORDER BY name',('student',)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


# ─────────────────────────────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────────────────────────────

print("\n=== ROUTES ===")
for rule in app.url_map.iter_rules():
    print(rule.methods, rule.rule)
print("=== END ROUTES ===\n")

@app.route('/api/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    conn = get_db()
    conn.execute('DELETE FROM results WHERE student_id = ?', (student_id,))
    conn.execute('DELETE FROM users WHERE id = ?', (student_id,))
    conn.commit()
    return jsonify({'success': True})
@app.route('/api/my-results')
def my_results():
    roll = request.args.get('roll', '')
    if not roll:
        return jsonify([])
    conn = get_db()
    results = conn.execute('''
        SELECT r.marks, r.total, r.subject, r.chapter_title,
               q.title as quiz_title, u.roll
        FROM results r
        JOIN quizzes q ON r.quiz_id = q.id
        JOIN users u ON r.student_id = u.id
        WHERE u.roll = ?
        ORDER BY r.submitted_at DESC
    ''', (roll,)).fetchall()
    return jsonify([dict(r) for r in results])
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)