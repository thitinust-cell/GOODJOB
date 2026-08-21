from flask import Flask, render_template, request, jsonify, session, redirect, Response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import uuid
import json
import pymysql
import pymysql.cursors
import os

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_USER_SECRET_KEY', 'demo-user-secret-key-change-me')

# เปลี่ยนชื่อ Session Cookie ไม่ให้ซ้ำกับฝั่ง Admin (พอร์ต 5002)
# ป้องกันปัญหาล็อกอินฝั่งนึง แล้วอีกฝั่งหลุด (Cookie Overwrite)
app.config['SESSION_COOKIE_NAME'] = 'eclipse_user_session'

# ตั้งค่าระยะเวลา Session สูงสุดเป็น 30 วัน
app.permanent_session_lifetime = timedelta(days=30)

# 🌟 ตั้งค่าโฟลเดอร์สำหรับเก็บรูปโปรไฟล์
app.config['UPLOAD_FOLDER'] = 'static/uploads/profiles'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 🌟 ตั้งค่าโฟลเดอร์สำหรับเก็บไฟล์แนบของพนักงาน
app.config['WORKER_ATTACHMENT_FOLDER'] = 'static/uploads/worker_attachments'
os.makedirs(app.config['WORKER_ATTACHMENT_FOLDER'], exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

# ==========================================
# Database Connection Helper
# ==========================================
def get_db_connection():
    return pymysql.connect(
        host=os.environ.get('MYSQLHOST', 'localhost'),
        user=os.environ.get('MYSQLUSER', 'root'),
        password=os.environ.get('MYSQLPASSWORD', ''),
        database=os.environ.get('MYSQLDATABASE', 'cls_ska'),
        port=int(os.environ.get('MYSQLPORT', '3306')),
        cursorclass=pymysql.cursors.DictCursor
    )

# ==========================================
# ⚙️ Centralized Branding Configuration
# ==========================================
@app.context_processor
def inject_brand_details():
    """ส่งชื่อและโลโก้ของแบรนด์ไปยัง Template ทุกหน้าโดยอัตโนมัติ"""
    return dict(
        BRAND_NAME="Demo Company",
        BRAND_LOGO_URL="/static/logo-eclipse.svg"
    )

# 🌟 ฟังก์ชันตรวจสอบนามสกุลไฟล์
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ฟังก์ชันสำหรับอัปเดตฐานข้อมูลอัตโนมัติ 
def check_and_update_db():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # ตรวจสอบว่ามีคอลัมน์ is_deleted_by_user หรือยัง
            cursor.execute("SHOW COLUMNS FROM requests LIKE 'is_deleted_by_user'")
            if not cursor.fetchone():
                print("[INFO] Updating Database... Adding 'is_deleted_by_user' column.")
                cursor.execute("ALTER TABLE requests ADD COLUMN is_deleted_by_user tinyint(1) DEFAULT 0")
                
            # 🌟 ตรวจสอบว่ามีคอลัมน์ vendor_company หรือยัง (บริษัท)
            cursor.execute("SHOW COLUMNS FROM requests LIKE 'vendor_company'")
            if not cursor.fetchone():
                print("[INFO] Updating Database... Adding 'vendor_company' column.")
                cursor.execute("ALTER TABLE requests ADD COLUMN vendor_company varchar(255) DEFAULT NULL AFTER company")
                
            # 🌟 ตรวจสอบว่ามีคอลัมน์ vehicle_reg หรือยัง (ทะเบียนรถ)
            cursor.execute("SHOW COLUMNS FROM requests LIKE 'vehicle_reg'")
            if not cursor.fetchone():
                print("[INFO] Updating Database... Adding 'vehicle_reg' column.")
                cursor.execute("ALTER TABLE requests ADD COLUMN vehicle_reg varchar(100) DEFAULT NULL AFTER mobile")
                
            # 🌟 ของ users (เพิ่มคอลัมน์เก็บชื่อไฟล์รูปโปรไฟล์ และช่องทางติดต่อเพิ่มเติม)
            cursor.execute("SHOW COLUMNS FROM users LIKE 'profile_pic'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN profile_pic varchar(255) DEFAULT NULL")
                print("[INFO] Added 'profile_pic' column.")
            
            cursor.execute("SHOW COLUMNS FROM users LIKE 'additional_emails'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN additional_emails TEXT DEFAULT NULL")
                print("[INFO] Added 'additional_emails' column.")
                
            cursor.execute("SHOW COLUMNS FROM users LIKE 'additional_phones'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN additional_phones TEXT DEFAULT NULL")
                print("[INFO] Added 'additional_phones' column.")

            conn.commit()
            print("[INFO] Database checked/updated successfully!")
        conn.close()
    except Exception as e:
        print(f"[WARNING] Database auto-update failed: {e}")

# ==========================================
# Routes (หน้าเว็บ) - ทำหน้าที่เสิร์ฟ HTML ปกติ
# ==========================================
@app.route('/')
def root():
    if 'user_id' not in session: return redirect('/login.html')
    return redirect('/dashboard.html')

@app.route('/login.html')
def login_page(): return render_template('login.html')

@app.route('/register.html')
def register_page(): return render_template('register.html')

@app.route('/forgot_password.html')
def forgot_password_page(): return render_template('forgot_password.html')

@app.route('/user_guide.html')
def user_guide_page(): return render_template('user_guide.html')

@app.route('/dashboard.html')
def dashboard_page():
    if 'user_id' not in session: return redirect('/login.html')
    return render_template('dashboard.html')

@app.route('/index.html')
def index_page():
    if 'user_id' not in session: return redirect('/login.html')
    return render_template('index.html')

@app.route('/view.html')
def view_page():
    if 'user_id' not in session: return redirect('/login.html')
    return render_template('view.html')

@app.route('/download.html')
def download_page():
    if 'user_id' not in session: return redirect('/login.html')
    return render_template('download.html')

@app.route('/success.html')
def success_page():
    if 'user_id' not in session: return redirect('/login.html')
    return render_template('success.html')

@app.route('/waiting_approval.html')
def waiting_approval_page():
    if 'user_id' not in session: 
        return redirect('/login.html')
    return render_template('waiting_approval.html')

# 🌟 Route สำหรับหน้าแก้ไข Profile (เดิมมีอยู่แล้ว)
@app.route('/user_edit_profile.html')
def profile_page():
    if 'user_id' not in session: 
        return redirect('/login.html')
    return render_template('user_edit_profile.html')

# 🌟 เพิ่ม Route สำหรับหน้าดู Profile (หน้าอ่านอย่างเดียว) ที่เพิ่งสร้างใหม่ 🌟
@app.route('/user_profile.html')
def view_profile_page():
    if 'user_id' not in session: 
        return redirect('/login.html')
    return render_template('user_profile.html')

# ==========================================
# API Endpoints (Authentication)
# ==========================================
@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.json
    username, email, password, full_name, phone = data.get('username'), data.get('email'), data.get('password'), data.get('full_name'), data.get('phone', '')
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone(): return jsonify({'success': False, 'message': 'ชื่อผู้ใช้งานนี้ถูกใช้ไปแล้ว'})
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone(): return jsonify({'success': False, 'message': 'อีเมลนี้ถูกใช้ลงทะเบียนไปแล้ว'})
            
            user_id = str(uuid.uuid4())[:8]
            hashed_pw = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO users (id, username, email, password_hash, full_name, phone, role, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, 'user', 'pending', NOW())
            """, (user_id, username, email, hashed_pw, full_name, phone))

            # ----------------------------------------------------------------------------------
            # 🌟 ส่วนที่เพิ่ม: ดึงรายชื่ออีเมลแอดมินทั้งหมด (ทั้ง admin และ superadmin) เพื่อแจ้งเตือน 🌟
            # ----------------------------------------------------------------------------------
            cursor.execute("SELECT email FROM users WHERE role IN ('admin', 'superadmin') AND email IS NOT NULL AND email != '' AND email != '-'")
            admins = cursor.fetchall()
            admin_emails_list = [admin['email'] for admin in admins if admin['email']]
            
            extra_admin_emails = [
                email.strip() for email in os.environ.get('EXTRA_ADMIN_ALERT_EMAILS', '').split(',') if email.strip()
            ]
            for email in extra_admin_emails:
                if email not in admin_emails_list:
                    admin_emails_list.append(email)

            admin_emails_str = ",".join(admin_emails_list)
            # ----------------------------------------------------------------------------------

        conn.commit()
        conn.close()
        
        # 🌟 ส่ง admin_emails กลับไปให้หน้าเว็บด้วย
        return jsonify({'success': True, 'message': 'ลงทะเบียนสำเร็จ', 'user_id': user_id, 'admin_emails': admin_emails_str})
    except Exception as e:
        return jsonify({'success': False, 'message': 'เกิดข้อผิดพลาดในการเชื่อมต่อฐานข้อมูล'}), 500

@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.json
    username, password, remember = data.get('username'), data.get('password'), data.get('remember', False)
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 🌟 แก้ไข: อนุญาตให้ทั้ง user, admin และ superadmin ล็อคอินฝั่งผู้ใช้ได้ 🌟
            cursor.execute("SELECT * FROM users WHERE username = %s AND role IN ('user', 'admin', 'superadmin')", (username,))
            user = cursor.fetchone()
            if user and check_password_hash(user['password_hash'], password):
                if user.get('status') == 'pending': return jsonify({'success': False, 'message': 'บัญชีอยู่ระหว่างรอตรวจสอบ'})
                if user.get('status') == 'rejected': return jsonify({'success': False, 'message': 'บัญชีไม่ได้รับการอนุมัติ'})
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['full_name'] = user['full_name']
                # 🌟 เก็บสิทธิ์ตามจริงที่ดึงมาจาก Database
                session['role'] = user['role']
                session.permanent = remember
                return jsonify({'success': True, 'redirect': '/dashboard.html'})
        conn.close()
        return jsonify({'success': False, 'message': 'ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'เกิดข้อผิดพลาดฐานข้อมูล'}), 500

@app.route('/api/reset_password', methods=['POST'])
def reset_password():
    try:
        data = request.json
        username = data.get('username')
        new_password = data.get('new_password')
        
        if not username or not new_password:
            return jsonify({'success': False, 'message': 'ข้อมูลไม่ครบถ้วน'}), 400
            
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s AND role = 'user'", (username,))
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'ไม่พบชื่อผู้ใช้งานนี้ในระบบ'}), 404
                
            hashed_pw = generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password_hash = %s WHERE username = %s AND role = 'user'", (hashed_pw, username))
            
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"DB Error (Reset Password): {e}")
        return jsonify({'success': False, 'message': 'เกิดข้อผิดพลาดในการเชื่อมต่อฐานข้อมูล'}), 500

@app.route('/api/logout')
def logout():
    session.clear()
    return redirect('/login.html')

@app.route('/api/user_profile')
def user_profile():
    if 'user_id' not in session: 
        return jsonify({'success': False}), 401
        
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 🌟 ดึงข้อมูลเพิ่มเติมมาด้วย
            cursor.execute("SELECT username, full_name, email, phone, profile_pic, additional_emails, additional_phones FROM users WHERE id = %s", (session['user_id'],))
            user = cursor.fetchone()
        conn.close()
        
        if user:
            return jsonify({
                'success': True, 
                'username': user['username'], 
                'full_name': user['full_name'],
                'email': user.get('email') or '-',
                'phone': user.get('phone') or '-',
                'profile_pic': user.get('profile_pic') or '',
                'additional_emails': user.get('additional_emails') or '[]',
                'additional_phones': user.get('additional_phones') or '[]'
            })
        return jsonify({'success': False, 'message': 'User not found'}), 404
        
    except Exception as e:
        print(f"DB Error (User Profile): {e}")
        # ถ้ามีปัญหาเชื่อมต่อ Database ให้ใช้ค่าจาก Session แก้ขัดไปก่อน
        return jsonify({
            'success': True, 
            'username': session.get('username'), 
            'full_name': session.get('full_name'),
            'email': '-',
            'phone': '-'
        })

# 🌟 API สำหรับรับข้อมูลแก้ไขโปรไฟล์ (มีรองรับรูปภาพ)
@app.route('/api/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session: 
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        full_name = request.form.get('full_name')
        email = request.form.get('email') # อีเมลหลัก
        phone = request.form.get('phone') # เบอร์หลัก
        additional_emails = request.form.get('additional_emails', '[]')
        additional_phones = request.form.get('additional_phones', '[]')
        user_id = session['user_id']
        
        profile_pic_path = None
        
        # 🌟 ระบบอัปโหลดและบันทึกรูปภาพ
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file.filename != '':
                # สร้างชื่อไฟล์ใหม่เพื่อป้องกันชื่อซ้ำกัน (ใช้ user_id นำหน้า)
                filename = secure_filename(f"{user_id}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                profile_pic_path = f"/static/uploads/profiles/{filename}"

        conn = get_db_connection()
        with conn.cursor() as cursor:
            # ถ้ามีการอัปโหลดรูป ให้บันทึกที่อยู่รูปด้วย ถ้าไม่มี ก็อัปเดตแค่ข้อความ
            if profile_pic_path:
                cursor.execute("""
                    UPDATE users 
                    SET full_name = %s, email = %s, phone = %s, profile_pic = %s, additional_emails = %s, additional_phones = %s
                    WHERE id = %s
                """, (full_name, email, phone, profile_pic_path, additional_emails, additional_phones, user_id))
            else:
                cursor.execute("""
                    UPDATE users 
                    SET full_name = %s, email = %s, phone = %s, additional_emails = %s, additional_phones = %s
                    WHERE id = %s
                """, (full_name, email, phone, additional_emails, additional_phones, user_id))
                
            # อัปเดต Session ชื่อให้เป็นปัจจุบันทันที
            session['full_name'] = full_name
            
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'อัปเดตโปรไฟล์สำเร็จ'})
        
    except Exception as e:
        print(f"DB Error (Update Profile): {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==========================================
# API Endpoints (Data Management)
# ==========================================
@app.route('/save_data', methods=['POST'])
def save_data():
    if 'user_id' not in session: return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        req_type = request.form.get('req_type', '')
        req_cat = request.form.get('req_cat', '')
        req_date = request.form.get('req_date')
        req_time = request.form.get('req_time')
        company = request.form.get('company', '')
        vendor_company = request.form.get('vendor_company', '') 
        dcf = request.form.get('dcf', '')
        mobile = request.form.get('mobile', '')
        vehicle_reg = request.form.get('vehicle_reg', '') 
        requester_name = request.form.get('requester_name', '')
        objective = request.form.get('objective', '')
        detail_work = request.form.get('detail_work', '')
        
        work_types = json.dumps(request.form.getlist('work_type'))
        risk = request.form.get('risk', 'No')
        areas = json.dumps(request.form.getlist('area'))
        
        start_date = request.form.get('start_date')
        start_time = request.form.get('start_time')
        end_date = request.form.get('end_date')
        end_time = request.form.get('end_time')
        signature = request.form.get('signature', '')

        # 🌟🌟 ปรับปรุง: ระบบจัดการรายชื่อผู้ปฏิบัติงานและไฟล์แนบแบบไดนามิก 🌟🌟
        workers = []
        # วน loop ตามจำนวน `worker_name_i` ที่ส่งมา
        i = 1
        while f'worker_name_{i}' in request.form:
            w_name = request.form.get(f'worker_name_{i}')
            if w_name:
                worker_data = {
                    'name': w_name,
                    'phone': request.form.get(f'worker_phone_{i}', ''),
                     'pos': request.form.get(f'worker_pos_{i}', ''),
                     'attachment': None # Default value
                }

                # ตรวจสอบไฟล์แนบสำหรับผู้ปฏิบัติงานคนนี้
                file_key = f'worker_attachment_{i}'
                if file_key in request.files:
                    file = request.files[file_key]
                    if file and file.filename != '' and allowed_file(file.filename):
                        # สร้างชื่อไฟล์ใหม่ที่ปลอดภัยและไม่ซ้ำกัน
                        filename = secure_filename(f"{uuid.uuid4().hex[:8]}_{file.filename}")
                        filepath = os.path.join(app.config['WORKER_ATTACHMENT_FOLDER'], filename)
                        file.save(filepath)
                        worker_data['attachment'] = f"/static/uploads/worker_attachments/{filename}"
                workers.append(worker_data)
            i += 1
        workers_json = json.dumps(workers)

        conn = get_db_connection()
        with conn.cursor() as cursor:
            now = datetime.now()
            current_date_str = now.strftime('%Y%m%d')
            current_month_str = now.strftime('%Y%m')
            
            cursor.execute("SELECT id FROM requests WHERE id LIKE %s ORDER BY id DESC LIMIT 1", (f"AS{current_month_str}%",))
            last_record = cursor.fetchone()
            new_seq = (int(last_record['id'][-3:]) + 1) if last_record else 1
            req_id = f"AS{current_date_str}{new_seq:03d}"

            sql = """
                INSERT INTO requests 
                (id, user_id, username, req_type, req_cat, req_date, req_time, company, vendor_company, dcf, mobile, vehicle_reg, requester_name, 
                 objective, detail_work, work_types, risk, areas, start_date, start_time, end_date, end_time, 
                 workers, signature, status, created_at) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending', NOW())
            """
            cursor.execute(sql, (
                req_id, session['user_id'], session['username'], req_type, req_cat, req_date, req_time, company, vendor_company, dcf, mobile, vehicle_reg, requester_name,
                objective, detail_work, work_types, risk, areas, start_date, start_time, end_date, end_time,
                workers_json, signature
            ))

            # ----------------------------------------------------------------------------------
            # 🌟 ส่วนที่เพิ่ม: ดึงรายชื่ออีเมลแอดมินทั้งหมดเพื่อแจ้งเตือนเมื่อมีเอกสารใหม่เข้า 🌟
            # ----------------------------------------------------------------------------------
            cursor.execute("SELECT email FROM users WHERE role IN ('admin', 'superadmin') AND email IS NOT NULL AND email != '' AND email != '-'")
            admins = cursor.fetchall()
            admin_emails_list = [admin['email'] for admin in admins if admin['email']]

            extra_admin_emails = [
                email.strip() for email in os.environ.get('EXTRA_ADMIN_ALERT_EMAILS', '').split(',') if email.strip()
            ]
            for email in extra_admin_emails:
                if email not in admin_emails_list:
                    admin_emails_list.append(email)

            admin_emails_str = ",".join(admin_emails_list)
            # ----------------------------------------------------------------------------------

        conn.commit()
        conn.close()

        # 🌟 ส่ง admin_emails กลับไปให้ฝั่งหน้าเว็บ
        return jsonify({'success': True, 'id': req_id, 'file_link': '', 'admin_emails': admin_emails_str})
    except Exception as e:
        print(f"DB Error (Save Data): {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/my_requests', methods=['GET'])
def get_my_requests():
    if 'user_id' not in session: return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, req_date, objective, areas, status FROM requests WHERE user_id = %s AND (is_deleted_by_user = 0 OR is_deleted_by_user IS NULL) ORDER BY created_at DESC", (session['user_id'],))
            rows = cursor.fetchall()
            for row in rows:
                if row['req_date'] and hasattr(row['req_date'], 'strftime'): row['req_date'] = row['req_date'].strftime('%Y-%m-%d')
                elif row['req_date']: row['req_date'] = str(row['req_date'])
                if row['areas']:
                    try:
                        areas_list = json.loads(row['areas'])
                        row['areas'] = ", ".join(areas_list) if isinstance(areas_list, list) else row['areas']
                    except: pass
        conn.close()
        return jsonify({'success': True, 'data': rows})
    except Exception as e:
        return jsonify({'success': False, 'message': 'เกิดข้อผิดพลาดในการโหลดข้อมูล', 'error': str(e)}), 500

@app.route('/api/calendar_events', methods=['GET'])
def get_calendar_events():
    """
    คืนข้อมูลงานในเดือนที่ระบุ สำหรับปฏิทินหน้า Dashboard
    รูปแบบ: {"success": true, "data": {"2026-08-17": [{"id":.., "name":.., "status":.., "hotwork": true/false}, ...]}}
    - ใช้ช่วง start_date..end_date ของแต่ละคำขอ (ถ้าไม่มีให้ fallback เป็น req_date) เพื่อกระจายไอคอนลงทุกวันที่งานเกิดขึ้น
    - risk = 'Yes' ถือเป็นงาน Hotwork (มีไอคอนไฟ)
    - แสดงคำขอของ "ทุกคน" ไม่ใช่แค่ของผู้ใช้ที่ล็อกอิน เพราะปฏิทินนี้มีไว้ดูภาพรวมงานที่จะเข้าสถานีในแต่ละวัน
    """
    if 'user_id' not in session: return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        year = int(request.args.get('year'))
        month = int(request.args.get('month'))
        month_start = f"{year}-{month:02d}-01"
        next_month_start = f"{year+1}-01-01" if month == 12 else f"{year}-{month+1:02d}-01"

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, requester_name, username, status, risk, req_date, start_date, end_date, start_time, end_time, objective, areas
                FROM requests
                WHERE (is_deleted_by_user = 0 OR is_deleted_by_user IS NULL)
                  AND COALESCE(start_date, req_date) < %s
                  AND COALESCE(end_date, start_date, req_date) >= %s
            """, (next_month_start, month_start))
            rows = cursor.fetchall()
        conn.close()

        events = {}
        for r in rows:
            start = r['start_date'] or r['req_date']
            end = r['end_date'] or start
            if not start:
                continue

            def normalize_time(value):
                if isinstance(value, timedelta):
                    total_seconds = int(value.total_seconds())
                    hours, remainder = divmod(total_seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    return f"{hours:02d}:{minutes:02d}"
                return value

            d = start
            while d <= end:
                key = d.strftime('%Y-%m-%d')
                events.setdefault(key, []).append({
                    'id': r['id'],
                    'name': r['requester_name'] or r['username'],
                    'status': r['status'],
                    'hotwork': r['risk'] == 'Yes',
                    'start_time': normalize_time(r['start_time']),
                    'end_time': normalize_time(r['end_time']),
                    'objective': r['objective'],
                    'areas': r['areas'],
                    'username': r['username']
                })
                d += timedelta(days=1)

        return jsonify({'success': True, 'data': events})
    except Exception as e:
        print(f"DB Error (Calendar Events): {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/get_data', methods=['GET'])
def get_data():
    if 'user_id' not in session: return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    doc_id = request.args.get('id')
    
    # 🌟 เพิ่มคำสั่งตัดช่องว่าง (space) ออกจาก ID ป้องกันฐานข้อมูลหาไม่เจอ 🌟
    if doc_id: 
        doc_id = doc_id.strip()
        
    if not doc_id: return jsonify({'success': False, 'message': 'Invalid ID'}), 400
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM requests WHERE id = %s AND user_id = %s", (doc_id, session['user_id']))
            row = cursor.fetchone()
            if not row: return jsonify({'success': False, 'message': 'Data not found'})
                
            for field in ['req_date', 'start_date', 'end_date']:
                if row.get(field) and hasattr(row[field], 'strftime'): row[field] = row[field].strftime('%Y-%m-%d')
            for field in ['req_time', 'start_time', 'end_time']:
                if isinstance(row.get(field), timedelta):
                    total_seconds = int(row.get(field).total_seconds())
                    hours, remainder = divmod(total_seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    row[field] = f"{hours:02d}:{minutes:02d}"
                
            for field in ['work_types', 'areas', 'workers']:
                if row.get(field):
                    try: row[field] = json.loads(row[field])
                    except: row[field] = [] if field != 'workers' else []

            if isinstance(row.get('workers'), list):
                for i, w in enumerate(row['workers'], 1):
                    row[f'worker_name_{i}'] = w.get('name', '')
                    row[f'worker_phone_{i}'] = w.get('phone', '')
                    row[f'worker_pos_{i}'] = w.get('pos', '')

        conn.close()
        return jsonify({'success': True, 'data': row})
    except Exception as e:
        return jsonify({'success': False}), 500

@app.route('/delete_data', methods=['POST'])
def delete_data():
    if 'user_id' not in session: return jsonify({'success': False}), 401
    try:
        doc_id = request.json.get('id')
        
        # 🌟 เพิ่มคำสั่งตัดช่องว่างเช่นเดียวกัน 🌟
        if doc_id:
            doc_id = doc_id.strip()
            
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("UPDATE requests SET is_deleted_by_user = 1 WHERE id = %s AND user_id = %s", (doc_id, session['user_id']))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    port = 5001
    print("\n" + "="*50)
    print(f"[START] User Portal Running on: http://localhost:{port}")
    print(f"[INFO]  Connected to MySQL (XAMPP) Database 'cls_ska'")
    check_and_update_db()
    print("="*50 + "\n")
    app.run(host="0.0.0.0", port=5001, debug=True)