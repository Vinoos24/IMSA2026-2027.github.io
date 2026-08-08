from __future__ import annotations
import os, json, sqlite3, secrets, io
from pathlib import Path
from datetime import datetime
from functools import wraps
from urllib.parse import urljoin
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify, abort
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from PIL import Image
import qrcode
from dotenv import load_dotenv

BASE_DIR=Path(__file__).resolve().parent
load_dotenv(BASE_DIR/'.env')
DATA_DIR=Path(os.getenv('DATA_DIR', BASE_DIR/'data')).resolve()
UPLOAD_DIR=DATA_DIR/'uploads'
ACTIVITY_UPLOADS=UPLOAD_DIR/'activities'
SETTING_UPLOADS=UPLOAD_DIR/'settings'
DB_PATH=DATA_DIR/'imsa.db'
for p in (DATA_DIR,ACTIVITY_UPLOADS,SETTING_UPLOADS): p.mkdir(parents=True,exist_ok=True)

app=Flask(__name__)
app.secret_key=os.getenv('SECRET_KEY') or secrets.token_hex(32)
app.config['MAX_CONTENT_LENGTH']=24*1024*1024
ALLOWED={'jpg','jpeg','png','webp'}


def db():
    conn=sqlite3.connect(DB_PATH)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

def init_db():
    c=db()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL DEFAULT '');
    CREATE TABLE IF NOT EXISTS leadership(id INTEGER PRIMARY KEY AUTOINCREMENT,role TEXT,name TEXT,description TEXT,sort_order INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS divisions(slug TEXT PRIMARY KEY,name TEXT,coordinator TEXT,summary TEXT,tasks_json TEXT,outputs_json TEXT,principle TEXT,sort_order INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS members(id INTEGER PRIMARY KEY AUTOINCREMENT,division_slug TEXT NOT NULL,name TEXT NOT NULL,sort_order INTEGER DEFAULT 0,FOREIGN KEY(division_slug) REFERENCES divisions(slug) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS activities(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,division TEXT,date TEXT,description TEXT,created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS activity_photos(id INTEGER PRIMARY KEY AUTOINCREMENT,activity_id INTEGER NOT NULL,filename TEXT NOT NULL,sort_order INTEGER DEFAULT 0,FOREIGN KEY(activity_id) REFERENCES activities(id) ON DELETE CASCADE);
    ''')
    if not c.execute('SELECT 1 FROM settings LIMIT 1').fetchone():
        seed=json.loads((BASE_DIR/'seed.json').read_text(encoding='utf-8'))
        c.executemany('INSERT INTO settings(key,value) VALUES(?,?)',seed['settings'].items())
        for i,(role,name,description) in enumerate(seed['leadership']): c.execute('INSERT INTO leadership(role,name,description,sort_order) VALUES(?,?,?,?)',(role,name,description,i))
        for i,d in enumerate(seed['divisions']):
            c.execute('INSERT INTO divisions(slug,name,coordinator,summary,tasks_json,outputs_json,principle,sort_order) VALUES(?,?,?,?,?,?,?,?)',(d['slug'],d['name'],d['coordinator'],d['summary'],json.dumps(d['tasks'],ensure_ascii=False),json.dumps(d['outputs'],ensure_ascii=False),d['principle'],i))
            for j,m in enumerate(d['members']): c.execute('INSERT INTO members(division_slug,name,sort_order) VALUES(?,?,?)',(d['slug'],m,j))
    c.commit(); c.close()

def settings_dict(c=None):
    own=c is None; c=c or db(); out={r['key']:r['value'] for r in c.execute('SELECT key,value FROM settings')}
    if own:c.close()
    return out

def get_content():
    c=db(); settings=settings_dict(c)
    leadership=[dict(r) for r in c.execute('SELECT * FROM leadership ORDER BY sort_order,id')]
    divisions=[]
    for r in c.execute('SELECT * FROM divisions ORDER BY sort_order,slug'):
        d=dict(r); d['tasks']=json.loads(d.pop('tasks_json') or '[]'); d['outputs']=json.loads(d.pop('outputs_json') or '[]')
        d['members']=[dict(m) for m in c.execute('SELECT * FROM members WHERE division_slug=? ORDER BY sort_order,id',(d['slug'],))]
        divisions.append(d)
    activities=[]
    for r in c.execute('SELECT * FROM activities ORDER BY COALESCE(date,created_at) DESC,id DESC'):
        a=dict(r); a['photos']=[dict(p) for p in c.execute('SELECT * FROM activity_photos WHERE activity_id=? ORDER BY sort_order,id',(a['id'],))]; activities.append(a)
    c.close(); return settings,leadership,divisions,activities

def public_base_url():
    configured=(os.getenv('PUBLIC_BASE_URL') or '').strip().rstrip('/')
    if configured:return configured
    return request.url_root.rstrip('/')

def qr_target(): return public_base_url()+'/?device=android'

def allowed(filename): return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED

def save_image(file,target_dir,prefix='img'):
    if not file or not file.filename or not allowed(file.filename): raise ValueError('Format gambar harus JPG, PNG, atau WEBP.')
    ext=file.filename.rsplit('.',1)[1].lower(); name=f'{prefix}-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}-{secrets.token_hex(4)}.jpg'
    image=Image.open(file.stream).convert('RGB'); image.thumbnail((2200,1600),Image.Resampling.LANCZOS)
    image.save(target_dir/name,'JPEG',quality=86,optimize=True); return name

def admin_required(fn):
    @wraps(fn)
    def wrapper(*a,**kw):
        if not session.get('admin'): return redirect(url_for('admin_login',next=request.path))
        return fn(*a,**kw)
    return wrapper

def csrf_token():
    if '_csrf' not in session:session['_csrf']=secrets.token_urlsafe(24)
    return session['_csrf']

def require_csrf():
    if request.form.get('_csrf')!=session.get('_csrf'): abort(400,'CSRF token invalid')

app.jinja_env.globals['csrf_token']=csrf_token
app.jinja_env.globals['public_base_url']=public_base_url

@app.route('/')
def dashboard():
    settings,leadership,divisions,activities=get_content()
    return render_template('dashboard.html',settings=settings,leadership=leadership,divisions=divisions,activities=activities,android=request.args.get('device')=='android')

@app.route('/presentation')
def presentation():
    settings,leadership,divisions,activities=get_content(); return render_template('presentation.html',settings=settings,leadership=leadership,divisions=divisions,activities=activities)

@app.route('/qr.png')
def qr_png():
    qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=9,border=3); qr.add_data(qr_target()); qr.make(fit=True)
    image=qr.make_image(fill_color='#760018',back_color='white').convert('RGB'); buf=io.BytesIO(); image.save(buf,'PNG'); buf.seek(0)
    from flask import send_file
    return send_file(buf,mimetype='image/png',max_age=0)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename): return send_from_directory(UPLOAD_DIR,filename)

@app.route('/api/public-config')
def public_config(): return jsonify({'publicUrl':qr_target(),'isPublicConfigured':bool((os.getenv('PUBLIC_BASE_URL') or '').strip())})

@app.route('/admin/login',methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        password=request.form.get('password','')
        configured_hash=os.getenv('ADMIN_PASSWORD_HASH','').strip(); configured_plain=os.getenv('ADMIN_PASSWORD','imsa2026')
        ok=check_password_hash(configured_hash,password) if configured_hash else secrets.compare_digest(password,configured_plain)
        if ok:
            session.clear(); session['admin']=True; csrf_token(); return redirect(request.args.get('next') or url_for('admin_dashboard'))
        flash('Password admin salah.','error')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout(): session.clear(); return redirect(url_for('dashboard'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    settings,leadership,divisions,activities=get_content(); return render_template('admin_dashboard.html',settings=settings,leadership=leadership,divisions=divisions,activities=activities,public_url=qr_target())

@app.post('/admin/settings')
@admin_required
def admin_settings():
    require_csrf(); keys=['site_title','hero_title','hero_subtitle','hero_description','hero_caption','period','sk_number','sk_date','sk_validity','footer_text']
    c=db()
    for k in keys:c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,request.form.get(k,'')))
    file=request.files.get('hero_background')
    if file and file.filename:
        try:
            filename=save_image(file,SETTING_UPLOADS,'hero'); rel=f'settings/{filename}'
            old=c.execute("SELECT value FROM settings WHERE key='hero_background'").fetchone();
            c.execute("INSERT INTO settings(key,value) VALUES('hero_background',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(rel,))
            if old and old['value']:
                try:(UPLOAD_DIR/old['value']).unlink(missing_ok=True)
                except:pass
        except ValueError as e: flash(str(e),'error')
    c.commit();c.close(); flash('Pengaturan dashboard diperbarui.','success'); return redirect(url_for('admin_dashboard')+'#settings')

@app.post('/admin/leadership/<int:item_id>')
@admin_required
def admin_leadership(item_id):
    require_csrf(); c=db(); c.execute('UPDATE leadership SET role=?,name=?,description=? WHERE id=?',(request.form.get('role',''),request.form.get('name',''),request.form.get('description',''),item_id)); c.commit();c.close(); flash('Data pengurus diperbarui.','success'); return redirect(url_for('admin_dashboard')+'#leadership')

@app.post('/admin/division/<slug>')
@admin_required
def admin_division(slug):
    require_csrf(); tasks=[x.strip() for x in request.form.get('tasks','').splitlines() if x.strip()]; outputs=[x.strip() for x in request.form.get('outputs','').splitlines() if x.strip()]
    c=db(); c.execute('UPDATE divisions SET name=?,coordinator=?,summary=?,tasks_json=?,outputs_json=?,principle=? WHERE slug=?',(request.form.get('name',''),request.form.get('coordinator',''),request.form.get('summary',''),json.dumps(tasks,ensure_ascii=False),json.dumps(outputs,ensure_ascii=False),request.form.get('principle',''),slug)); c.commit();c.close(); flash('Data divisi diperbarui.','success'); return redirect(url_for('admin_dashboard')+f'#division-{slug}')

@app.post('/admin/member/add/<slug>')
@admin_required
def admin_member_add(slug):
    require_csrf(); name=request.form.get('name','').strip(); c=db();
    if name:
        order=c.execute('SELECT COALESCE(MAX(sort_order),-1)+1 n FROM members WHERE division_slug=?',(slug,)).fetchone()['n']; c.execute('INSERT INTO members(division_slug,name,sort_order) VALUES(?,?,?)',(slug,name,order)); c.commit()
    c.close(); return redirect(url_for('admin_dashboard')+f'#division-{slug}')

@app.post('/admin/member/<int:member_id>')
@admin_required
def admin_member_edit(member_id):
    require_csrf(); c=db(); r=c.execute('SELECT division_slug FROM members WHERE id=?',(member_id,)).fetchone();
    if not r:abort(404)
    c.execute('UPDATE members SET name=? WHERE id=?',(request.form.get('name','').strip(),member_id)); c.commit();c.close(); return redirect(url_for('admin_dashboard')+f'#division-{r["division_slug"]}')

@app.post('/admin/member/<int:member_id>/delete')
@admin_required
def admin_member_delete(member_id):
    require_csrf(); c=db(); r=c.execute('SELECT division_slug FROM members WHERE id=?',(member_id,)).fetchone();
    if not r:abort(404)
    c.execute('DELETE FROM members WHERE id=?',(member_id,));c.commit();c.close(); return redirect(url_for('admin_dashboard')+f'#division-{r["division_slug"]}')

@app.post('/admin/activity')
@admin_required
def admin_activity_create():
    require_csrf(); title=request.form.get('title','').strip()
    if not title: flash('Judul kegiatan wajib diisi.','error'); return redirect(url_for('admin_dashboard')+'#activities')
    c=db(); cur=c.execute('INSERT INTO activities(title,division,date,description,created_at) VALUES(?,?,?,?,?)',(title,request.form.get('division',''),request.form.get('date',''),request.form.get('description',''),datetime.utcnow().isoformat())); aid=cur.lastrowid
    for i,file in enumerate(request.files.getlist('photos')[:8]):
        if file and file.filename:
            try: fn=save_image(file,ACTIVITY_UPLOADS,f'act{aid}'); c.execute('INSERT INTO activity_photos(activity_id,filename,sort_order) VALUES(?,?,?)',(aid,f'activities/{fn}',i))
            except ValueError as e: flash(str(e),'error')
    c.commit();c.close(); flash('Kegiatan ditambahkan.','success'); return redirect(url_for('admin_dashboard')+'#activities')

@app.post('/admin/activity/<int:activity_id>')
@admin_required
def admin_activity_edit(activity_id):
    require_csrf(); c=db(); c.execute('UPDATE activities SET title=?,division=?,date=?,description=? WHERE id=?',(request.form.get('title',''),request.form.get('division',''),request.form.get('date',''),request.form.get('description',''),activity_id))
    existing=c.execute('SELECT COALESCE(MAX(sort_order),-1)+1 n FROM activity_photos WHERE activity_id=?',(activity_id,)).fetchone()['n']
    for i,file in enumerate(request.files.getlist('photos')[:8]):
        if file and file.filename:
            try:fn=save_image(file,ACTIVITY_UPLOADS,f'act{activity_id}');c.execute('INSERT INTO activity_photos(activity_id,filename,sort_order) VALUES(?,?,?)',(activity_id,f'activities/{fn}',existing+i))
            except ValueError as e:flash(str(e),'error')
    c.commit();c.close();flash('Kegiatan diperbarui.','success');return redirect(url_for('admin_dashboard')+'#activities')

@app.post('/admin/photo/<int:photo_id>/delete')
@admin_required
def admin_photo_delete(photo_id):
    require_csrf(); c=db(); r=c.execute('SELECT activity_id,filename FROM activity_photos WHERE id=?',(photo_id,)).fetchone();
    if not r:abort(404)
    c.execute('DELETE FROM activity_photos WHERE id=?',(photo_id,));c.commit();c.close()
    try:(UPLOAD_DIR/r['filename']).unlink(missing_ok=True)
    except:pass
    return redirect(url_for('admin_dashboard')+'#activities')

@app.post('/admin/activity/<int:activity_id>/delete')
@admin_required
def admin_activity_delete(activity_id):
    require_csrf(); c=db(); files=[r['filename'] for r in c.execute('SELECT filename FROM activity_photos WHERE activity_id=?',(activity_id,))];c.execute('DELETE FROM activities WHERE id=?',(activity_id,));c.commit();c.close()
    for f in files:
        try:(UPLOAD_DIR/f).unlink(missing_ok=True)
        except:pass
    flash('Kegiatan dihapus.','success');return redirect(url_for('admin_dashboard')+'#activities')

@app.context_processor
def helpers():
    return {'upload_url':lambda rel:url_for('uploaded_file',filename=rel) if rel else ''}

if __name__=='__main__':
    init_db(); app.run(host='0.0.0.0',port=int(os.getenv('PORT','5000')),debug=os.getenv('FLASK_DEBUG')=='1')
else:
    init_db()
