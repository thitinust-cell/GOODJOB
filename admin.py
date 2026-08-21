from flask import Flask, render_template, request, jsonify, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename 
import uuid
import jinja2
from datetime import datetime, timedelta
import json
import pymysql
import pymysql.cursors
import os 

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_ADMIN_SECRET_KEY', 'demo-admin-secret-key-change-me')

#เปลี่ยนชื่อ Session Cookie ไม่ให้ซ้ำกับฝั่ง User (พอร์ต 5001)
app.config['SESSION_COOKIE_NAME'] = 'eclipse_admin_session' 

app.permanent_session_lifetime = timedelta(days=30) 

app.config['UPLOAD_FOLDER'] = 'static/uploads/profiles'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ==========================================
# 🛠 Database Connection Helper
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

# 🌟 ปรับปรุงฟังก์ชันอัปเดตฐานข้อมูลอัตโนมัติให้รองรับ Super Admin 🌟
def check_and_update_db():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # ตรวจสอบว่ามีคอลัมน์ is_deleted_by_user หรือยัง
            cursor.execute("SHOW COLUMNS FROM requests LIKE 'is_deleted_by_user'")
            if not cursor.fetchone():
                print("[INFO] Updating Database... Adding 'is_deleted_by_user' column.")
                cursor.execute("ALTER TABLE requests ADD COLUMN is_deleted_by_user tinyint(1) DEFAULT 0")
                
            # ตรวจสอบว่ามีคอลัมน์ vendor_company หรือยัง (บริษัท)
            cursor.execute("SHOW COLUMNS FROM requests LIKE 'vendor_company'")
            if not cursor.fetchone():
                print("[INFO] Updating Database... Adding 'vendor_company' column.")
                cursor.execute("ALTER TABLE requests ADD COLUMN vendor_company varchar(255) DEFAULT NULL AFTER company")
                
            # ตรวจสอบว่ามีคอลัมน์ vehicle_reg หรือยัง (ทะเบียนรถ)
            cursor.execute("SHOW COLUMNS FROM requests LIKE 'vehicle_reg'")
            if not cursor.fetchone():
                print("[INFO] Updating Database... Adding 'vehicle_reg' column.")
                cursor.execute("ALTER TABLE requests ADD COLUMN vehicle_reg varchar(100) DEFAULT NULL AFTER mobile")
                
            # ของ users (เพิ่มคอลัมน์เก็บชื่อไฟล์รูปโปรไฟล์ และช่องทางติดต่อเพิ่มเติม)
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

            # ปรับแอดมินเดิมในระบบให้เป็น active เพื่อป้องกันการล็อคอินไม่ได้
            cursor.execute("UPDATE users SET status = 'active' WHERE role = 'admin' AND status = 'pending'")

            conn.commit()
            print("[INFO] Database checked/updated successfully!")
        conn.close()
    except Exception as e:
        print(f"[WARNING] Database auto-update failed: {e}")

# ==========================================
# --- Routes (หน้าเว็บสำหรับ Admin) ---
# ==========================================

@app.route('/')
def root():
    if 'admin_id' in session:
        return redirect('/admin_dashboard.html')
    return redirect('/admin_login.html')

@app.route('/admin_login.html')
def login_page():
    return render_template('admin_login.html')

@app.route('/admin_register.html')
def register_page():
    return render_template('admin_register.html')

@app.route('/forgot_password.html')
def forgot_password_page():
    return render_template('forgot_password.html')

#เพิ่ม Route สำหรับหน้าคู่มือแอดมิน (เปิดได้ทุกคน ไม่ต้องล็อคอิน) 
@app.route('/admin_guide.html')
def admin_guide_page():
    return render_template('admin_guide.html')

@app.route('/admin_dashboard.html')
def dashboard_page():
    if 'admin_id' not in session:
        return redirect('/admin_login.html')
        
    try:
        return render_template('admin_dashboard.html')
    except jinja2.exceptions.TemplateNotFound:
        return render_template('admin_dashboard.html')

@app.route('/admin_approve.html')
@app.route('/approve.html') 
def approve_page():
    if 'admin_id' not in session:
        return redirect('/admin_login.html')
    return render_template('admin_approve.html')

@app.route('/admin_download.html')
@app.route('/download.html') 
def download_page():
    if 'admin_id' not in session:
        return redirect('/admin_login.html')
    return render_template('admin_download.html')

@app.route('/admin_view.html')
def view_page():
    if 'admin_id' not in session:
        return redirect('/admin_login.html')
    return render_template('admin_view.html')

@app.route('/admin_success.html')
def success_page():
    if 'admin_id' not in session:
        return redirect('/admin_login.html')
    return render_template('admin_success.html')

# เพิ่ม Route สำหรับหน้าดูรายละเอียดผู้ใช้ของแอดมิน
@app.route('/admin_view_user.html')
def admin_view_user_page():
    if 'admin_id' not in session: 
        return redirect('/admin_login.html')
    return render_template('admin_view_user.html')

# 🌟 เพิ่ม Route สำหรับหน้าแก้ไขโปรไฟล์ส่วนตัวของแอดมิน 🌟
@app.route('/admin_edit_profile.html')
def admin_edit_profile_page():
    if 'admin_id' not in session: 
        return redirect('/admin_login.html')
    return render_template('admin_edit_profile.html')

# ==========================================
# --- API: Authentication & Profile ---
# ==========================================

@app.route('/api/admin/register', methods=['POST'])
def admin_register():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        full_name = data.get('full_name')
        email = data.get('email', '') # 🌟 รับค่าอีเมลจากหน้าเว็บ 🌟
        phone = data.get('phone', '') # 🌟 รับค่าเบอร์โทรจากหน้าเว็บ 🌟
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # เช็คว่ามี username อยู่หรือยัง
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return jsonify({'success': False, 'message': 'Username already exists'}), 409
            
            # เช็คว่ามี email อยู่หรือยัง (ถ้ามีการกรอกมา)
            if email:
                cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
                if cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Email already exists'}), 409
            
            user_id = str(uuid.uuid4())[:8]
            hashed_pw = generate_password_hash(password)

            # สมัครแอดมินตาม流程ปกติเท่านั้น ไม่เปิดช่องเข้าสู่ superadmin แบบลับ
            role = 'admin'
            status = 'pending'

            # 🌟 บันทึก email และ phone ลงฐานข้อมูลด้วย 🌟
            cursor.execute("""
                INSERT INTO users (id, username, password_hash, full_name, email, phone, role, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (user_id, username, hashed_pw, full_name, email, phone, role, status))

            # ------------------------------------------------------------------------
            # 🌟 ดึงอีเมลเฉพาะ Super Admin และ อีเมลกลาง เพื่อแจ้งเตือนคนสมัคร Admin 🌟
            # ------------------------------------------------------------------------
            cursor.execute("SELECT email FROM users WHERE role = 'superadmin' AND email IS NOT NULL AND email != '' AND email != '-'")
            admins = cursor.fetchall()
            admin_emails_list = [admin['email'] for admin in admins if admin['email']]
            
            extra_admin_emails = [
                email.strip() for email in os.environ.get('EXTRA_ADMIN_ALERT_EMAILS', '').split(',') if email.strip()
            ]
            for email in extra_admin_emails:
                if email not in admin_emails_list:
                    admin_emails_list.append(email)

            admin_emails_str = ",".join(admin_emails_list)

        conn.commit()
        conn.close()
        
        # 🌟 คืนค่า admin_emails ไปให้ฝั่ง Frontend ส่งเข้า Google Apps Script 🌟
        return jsonify({'success': True, 'message': 'Admin created successfully', 'admin_emails': admin_emails_str})
    except Exception as e:
        print(f"[ERROR] Admin Register: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        remember = data.get('remember', False)
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 🌟 ตรวจสอบทั้ง admin และ superadmin 🌟
            cursor.execute("SELECT * FROM users WHERE username = %s AND role IN ('admin', 'superadmin')", (username,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password_hash'], password):
                
                # 🌟 ตรวจสอบสถานะว่าบัญชีโดนดองหรือโดนเตะหรือไม่ 🌟
                if user.get('status') == 'pending':
                    return jsonify({'success': False, 'message': 'บัญชีแอดมินของคุณอยู่ระหว่างรออนุมัติสิทธิ์จาก Super Admin'})
                if user.get('status') == 'rejected':
                    return jsonify({'success': False, 'message': 'บัญชีผู้ดูแลระบบของคุณไม่ได้รับการอนุมัติสิทธิ์'})

                session['admin_id'] = user['id']
                session['admin_name'] = user['full_name']
                session['admin_role'] = user['role'] # 🌟 เก็บ Role ไว้เช็คสิทธิ์ในระบบ
                session.permanent = remember
                return jsonify({'success': True})
                
        conn.close()
        return jsonify({'success': False, 'message': 'Invalid credentials or not an admin'}), 401
    except Exception as e:
        print(f"[ERROR] Admin Login: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/reset_password', methods=['POST'])
def reset_password():
    try:
        data = request.json
        username = data.get('username')
        new_password = data.get('new_password')
        
        if not username or not new_password:
            return jsonify({'success': False, 'message': 'ข้อมูลไม่ครบถ้วน'}), 400
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 🌟 ยอมให้ทั้ง admin และ superadmin เปลี่ยนรหัสได้ 🌟
            cursor.execute("SELECT id FROM users WHERE username = %s AND role IN ('admin', 'superadmin')", (username,))
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': 'ไม่พบชื่อผู้ใช้งานนี้ในระบบ'}), 404
                
            hashed_pw = generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password_hash = %s WHERE username = %s AND role IN ('admin', 'superadmin')", (hashed_pw, username))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] Reset Password: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/logout')
def logout():
    session.clear()
    return redirect('/admin_login.html')

# 🌟 อัปเดต API โหลดโปรไฟล์แอดมินให้ดึงข้อมูลใหม่ๆ มาแสดงในหน้า Edit Profile ด้วย 🌟
@app.route('/api/user_profile')
def user_profile():
    if 'admin_id' not in session:
        return jsonify({'success': False}), 401
        
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT username, full_name, email, phone, profile_pic, additional_emails, additional_phones, role 
                FROM users WHERE id = %s
            """, (session['admin_id'],))
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
                'additional_phones': user.get('additional_phones') or '[]',
                'role': user['role']
            })
        return jsonify({'success': False, 'message': 'User not found'}), 404
        
    except Exception as e:
        print(f"DB Error (Admin Profile): {e}")
        # ถ้า Database เออเร่อ ให้ส่งข้อมูลพื้นฐานจาก session เผื่อไว้
        return jsonify({'success': True, 'full_name': session['admin_name'], 'role': session.get('admin_role', 'admin')})

# 🌟 เพิ่ม API สำหรับให้แอดมินอัปเดตโปรไฟล์ตัวเอง (รองรับเพิ่มรูป, อีเมลเสริม, เบอร์เสริม) 🌟
@app.route('/api/admin/update_profile', methods=['POST'])
def admin_update_profile():
    if 'admin_id' not in session: 
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        admin_id = session['admin_id']
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        additional_emails = request.form.get('additional_emails', '[]')
        additional_phones = request.form.get('additional_phones', '[]')
        
        profile_pic_path = None
        
        # จัดการการอัปโหลดไฟล์รูป
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file.filename != '':
                filename = secure_filename(f"admin_{admin_id}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                profile_pic_path = f"/static/uploads/profiles/{filename}"

        conn = get_db_connection()
        with conn.cursor() as cursor:
            if profile_pic_path:
                cursor.execute("""
                    UPDATE users 
                    SET full_name=%s, email=%s, phone=%s, profile_pic=%s, additional_emails=%s, additional_phones=%s 
                    WHERE id=%s
                """, (full_name, email, phone, profile_pic_path, additional_emails, additional_phones, admin_id))
            else:
                cursor.execute("""
                    UPDATE users 
                    SET full_name=%s, email=%s, phone=%s, additional_emails=%s, additional_phones=%s 
                    WHERE id=%s
                """, (full_name, email, phone, additional_emails, additional_phones, admin_id))
            
            # อัปเดตชื่อใน session เผื่อมีการเปลี่ยนชื่อ
            session['admin_name'] = full_name 
            
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    except Exception as e:
        print(f"DB Error (Admin Update Profile): {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ==========================================
# --- API: Data Management ---
# ==========================================

@app.route('/api/admin/get_all_requests', methods=['GET'])
@app.route('/api/my_requests', methods=['GET']) 
def get_all():
    if 'admin_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # ดึงข้อมูลทั้งหมดมาแสดงในตาราง Dashboard
            cursor.execute("SELECT id, req_date, requester_name, company, objective, status FROM requests ORDER BY created_at DESC")
            rows = cursor.fetchall()
            
            for row in rows:
                if row['req_date']: 
                    row['req_date'] = row['req_date'].strftime('%Y-%m-%d')
                    
        conn.close()
        return jsonify({'success': True, 'data': rows})
    except Exception as e:
        print(f"[ERROR] Get All Requests: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/get_users', methods=['GET'])
def get_users():
    if 'admin_id' not in session:
        return jsonify({'success': False}), 401
    try:
        admin_role = session.get('admin_role', 'admin')
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 🌟 ถ้าเป็น Super Admin ให้ดึงข้อมูลทั้ง User และ Admin (คนอื่น) มาแสดงด้วย
            if admin_role == 'superadmin':
                cursor.execute("""
                    SELECT id, username, email, full_name, phone, status, role, created_at, profile_pic 
                    FROM users 
                    WHERE role IN ('user', 'admin') AND id != %s 
                    ORDER BY role ASC, created_at DESC
                """, (session['admin_id'],))
            else:
                # ถ้าเป็น Admin ธรรมดา ให้เห็นแค่ User ปกติ
                cursor.execute("""
                    SELECT id, username, email, full_name, phone, status, role, created_at, profile_pic 
                    FROM users 
                    WHERE role = 'user' 
                    ORDER BY created_at DESC
                """)
            users = cursor.fetchall()
            
            for user in users:
                if user['created_at']:
                    user['created_at'] = user['created_at'].strftime('%Y-%m-%d %H:%M')
                    
        conn.close()
        return jsonify({'success': True, 'data': users, 'total_users': len(users)})
    except Exception as e:
        print(f"[ERROR] Get Users: {e}")
        return jsonify({'success': False, 'data': [], 'total_users': 0}), 500

# เพิ่ม API สำหรับดึงข้อมูล User ตาม ID เพื่อมาแสดงในหน้ารายละเอียดผู้ใช้งาน (admin_view_user.html)
@app.route('/api/admin/get_user_detail', methods=['GET'])
def admin_get_user_detail():
    if 'admin_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    target_user_id = request.args.get('id')
    if not target_user_id:
        return jsonify({'success': False, 'message': 'Missing user ID'}), 400

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, username, full_name, email, phone, role, status, created_at, 
                       profile_pic, additional_emails, additional_phones 
                FROM users WHERE id = %s
            """, (target_user_id,))
            user = cursor.fetchone()
        conn.close()

        if user:
            if user['created_at']:
                user['created_at'] = user['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            
            # แปลงข้อมูลอีเมลและเบอร์โทรเพิ่มเติมจาก JSON กลับเป็น List
            for field in ['additional_emails', 'additional_phones']:
                if user.get(field):
                    try: user[field] = json.loads(user[field])
                    except: user[field] = []
                else:
                    user[field] = []

            return jsonify({'success': True, 'data': user})
        else:
            return jsonify({'success': False, 'message': 'ไม่พบผู้ใช้งานนี้'}), 404
            
    except Exception as e:
        print(f"[ERROR] Admin Get User Detail: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# 🌟 อัปเดตสิทธิ์การอนุมัติผู้ใช้งาน (เฉพาะ Super Admin เท่านั้น) 🌟
@app.route('/api/admin/update_user_status', methods=['POST'])
def update_user_status():
    if 'admin_id' not in session:
        return jsonify({'success': False}), 401
        
    # บล็อคแอดมินธรรมดา ไม่ให้อนุมัติคนได้
    if session.get('admin_role') != 'superadmin':
        return jsonify({'success': False, 'message': 'Permission Denied: เฉพาะ Super Admin เท่านั้นที่ทำรายการนี้ได้'}), 403

    try:
        data = request.json
        user_id = data.get('user_id')
        new_status = data.get('status')
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            if new_status == 'rejected':
                # ลบรายชื่อผู้ใช้ออกจากฐานข้อมูล XAMPP เมื่อกดปฏิเสธ
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            else:
                # อนุมัติสิทธิ์ (เปลี่ยนสถานะเป็น active)
                cursor.execute("UPDATE users SET status = %s WHERE id = %s", (new_status, user_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] Update User Status: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# 🌟 อัปเดตสิทธิ์การลบผู้ใช้งาน (เฉพาะ Super Admin เท่านั้น) 🌟
@app.route('/api/admin/delete_user', methods=['POST'])
def delete_user():
    if 'admin_id' not in session:
        return jsonify({'success': False}), 401
        
    # บล็อคแอดมินธรรมดา ไม่ให้ลบคนได้
    if session.get('admin_role') != 'superadmin':
        return jsonify({'success': False, 'message': 'Permission Denied: เฉพาะ Super Admin เท่านั้นที่ลบบัญชีผู้ใช้ได้'}), 403

    try:
        data = request.json
        user_id = data.get('user_id')
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'User deleted successfully'})
    except Exception as e:
        print(f"[ERROR] Delete User: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# 🌟 เพิ่ม API สำหรับเปลี่ยนระดับสิทธิ์ (เฉพาะ Super Admin) 🌟
@app.route('/api/admin/change_role', methods=['POST'])
def change_role():
    if 'admin_id' not in session:
        return jsonify({'success': False}), 401
        
    if session.get('admin_role') != 'superadmin':
        return jsonify({'success': False, 'message': 'Permission Denied: เฉพาะ Super Admin เท่านั้นที่สามารถเปลี่ยนสิทธิ์ได้'}), 403

    try:
        data = request.json
        user_id = data.get('user_id')
        new_role = data.get('role')
        
        if new_role not in ['user', 'admin']:
            return jsonify({'success': False, 'message': 'Invalid role'}), 400
            
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # ป้องกันการเผลอไปเปลี่ยนสิทธิ์ของ Super Admin คนอื่นๆ
            cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
            u = cursor.fetchone()
            if u and u['role'] == 'superadmin':
                return jsonify({'success': False, 'message': 'ไม่สามารถลดระดับหรือแก้ไขสิทธิ์ของ Super Admin ได้'}), 403
                
            cursor.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Role updated successfully'})
    except Exception as e:
        print(f"[ERROR] Change Role: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# 🌟 เพิ่ม API สำหรับลบรายการคำขอเข้าพื้นที่ (Super Admin ลบได้ แอดมินธรรมดาลบไม่ได้) 🌟
@app.route('/api/admin/delete_request', methods=['POST'])
def delete_request():
    if 'admin_id' not in session:
        return jsonify({'success': False}), 401
        
    if session.get('admin_role') != 'superadmin':
        return jsonify({'success': False, 'message': 'Permission Denied: เฉพาะ Super Admin เท่านั้นที่ลบเอกสารคำขอได้'}), 403

    try:
        data = request.json
        req_id = data.get('req_id')
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM requests WHERE id = %s", (req_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Request deleted successfully'})
    except Exception as e:
        print(f"[ERROR] Delete Request: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/get_data', methods=['GET'])
def get_data_proxy():
    if 'admin_id' not in session:
        return jsonify({'success': False}), 401
    try:
        doc_id = request.args.get('id')
        if doc_id: doc_id = doc_id.strip() # ป้องกันช่องว่างที่ติดมากับ ID
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM requests WHERE id = %s", (doc_id,))
            row = cursor.fetchone()
            
            if not row: 
                return jsonify({'success': False, 'message': 'Data not found'})
                
            # อัปเดตการแปลงวันที่ให้ปลอดภัยยิ่งขึ้น ป้องกันการดึงข้อมูลพลาด
            for field in ['req_date', 'start_date', 'end_date']:
                if row.get(field) and hasattr(row[field], 'strftime'): 
                    row[field] = row[field].strftime('%Y-%m-%d')
            
            for field in ['req_time', 'start_time', 'end_time']:
                if isinstance(row.get(field), timedelta):
                    total_seconds = int(row[field].total_seconds())
                    hours, remainder = divmod(total_seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    row[field] = f"{hours:02d}:{minutes:02d}"
                elif row.get(field):
                    row[field] = str(row[field])
                
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
        print(f"[Error] Get Data Proxy: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/update_status', methods=['POST'])
def update_status():
    if 'admin_id' not in session:
        return jsonify({'success': False}), 401
    try:
        data = request.json
        req_id = data['id']
        status = data['status']
        approver_name = session.get('admin_name', data.get('approver_name', 'Admin'))
        approver_comment = data.get('approver_comment', '')
        approver_signature = data.get('approver_signature', '')

        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """
                UPDATE requests 
                SET status=%s, approver_name=%s, approver_comment=%s, approver_signature=%s 
                WHERE id=%s
            """
            cursor.execute(sql, (status, approver_name, approver_comment, approver_signature, req_id))
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': 'Not found in DB'}), 404
                
            # ดึงอีเมลของผู้ใช้เพื่อส่งกลับไปให้หน้าเว็บยิงแจ้งเตือน 
            cursor.execute("""
                SELECT u.email 
                FROM requests r 
                JOIN users u ON r.user_id = u.id 
                WHERE r.id = %s
            """, (req_id,))
            user_info = cursor.fetchone()
            user_email = user_info['email'] if user_info else ''
            
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'user_email': user_email})
    except Exception as e:
        print(f"[ERROR] Update Status: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*50)
    print("ADMIN SERVER Running on: http://localhost:5002")
    print("Connected to MySQL (XAMPP) Database 'cls_ska'")
    print("="*50 + "\n")
    check_and_update_db()
    app.run(host='0.0.0.0', port=5002, debug=True)