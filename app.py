import os, sqlite3, secrets
from functools import wraps
from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__, static_folder=None)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
DB_PATH = os.environ.get("DB_PATH", "/tmp/sofia_orders.sqlite3")
ADMIN_USER = os.environ.get("ADMIN_USER", "sofia")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

def db():
    conn=sqlite3.connect(DB_PATH)
    conn.row_factory=sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS orders (
      id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT DEFAULT (datetime('now')),
      name TEXT NOT NULL, phone TEXT NOT NULL, date TEXT, guests TEXT, address TEXT, product TEXT, comment TEXT,
      status TEXT NOT NULL DEFAULT 'Новая')""")
    conn.commit()
    return conn

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args,**kwargs):
        if not session.get("admin"): return redirect(url_for("login", next=request.path))
        return fn(*args,**kwargs)
    return wrapper

@app.get("/")
def home():
    return send_from_directory(base_dir(), "index.html")

def base_dir():
    return os.path.dirname(os.path.abspath(__file__))

@app.get("/health")
def health():
    return jsonify(status="ok")

@app.post("/api/orders")
def create_order():
    data=request.get_json(silent=True) or {}
    name=str(data.get("name","")).strip()
    phone=str(data.get("phone","")).strip()
    if not name or not phone:
        return jsonify(error="Укажите имя и телефон"),400
    with db() as conn:
        cur=conn.execute("INSERT INTO orders(name,phone,date,guests,address,product,comment) VALUES(?,?,?,?,?,?,?)",
          (name[:120],phone[:80],str(data.get("date",""))[:30],str(data.get("guests",""))[:80],
           str(data.get("address",""))[:250],str(data.get("product",""))[:120],str(data.get("comment",""))[:2000]))
        oid=cur.lastrowid
    return jsonify(ok=True,id=oid)

LOGIN = """<!doctype html><html lang=ru><meta name=viewport content="width=device-width,initial-scale=1"><title>Вход администратора</title>
<style>body{font:16px Arial;background:#faf5ed;color:#44352b;display:grid;place-items:center;min-height:100vh;margin:0}.box{background:white;padding:28px;border-radius:18px;max-width:360px;width:calc(100% - 56px);box-shadow:0 8px 30px #0001}input,button{box-sizing:border-box;width:100%;padding:12px;margin:8px 0;border:1px solid #ddd;border-radius:8px}button{background:#9a7748;color:white;border:0;font-weight:bold}.err{color:#a22}</style>
<div class=box><h2>Панель Sofia Sweet Moments</h2><p>Войдите, чтобы посмотреть заявки.</p>{% if error %}<p class=err>{{error}}</p>{% endif %}<form method=post><input name=username placeholder="Логин" required><input name=password type=password placeholder="Пароль" required><button>Войти</button></form></div></html>"""
DASH = """<!doctype html><html lang=ru><meta name=viewport content="width=device-width,initial-scale=1"><title>Заявки</title>
<style>body{font:15px Arial;background:#faf5ed;color:#44352b;margin:0;padding:18px}h1{font-size:24px}.top{display:flex;justify-content:space-between;align-items:center;gap:12px}a,button{color:#805e32}table{border-collapse:collapse;width:100%;background:#fff;border-radius:12px;overflow:hidden}th,td{padding:10px;border-bottom:1px solid #eee;text-align:left;vertical-align:top}th{background:#efe3d1}select,button{padding:8px;border:1px solid #ddd;border-radius:6px} .wrap{overflow-x:auto}small{color:#777}</style>
<div class=top><div><h1>Заявки · Sofia Sweet Moments</h1><small>Всего: {{orders|length}}</small></div><a href="/admin/logout">Выйти</a></div>
{% if orders %}<div class=wrap><table><thead><tr><th>№ / Дата</th><th>Клиент</th><th>Заказ</th><th>Статус</th><th></th></tr></thead><tbody>
{% for o in orders %}<tr><td>#{{o.id}}<br><small>{{o.created_at}} UTC</small></td><td><b>{{o.name}}</b><br><a href="tel:{{o.phone}}">{{o.phone}}</a></td><td>{{o.product}}<br>{{o.date}} · {{o.guests}}<br>{{o.address}}<br>{{o.comment}}</td><td>{{o.status}}</td><td><form method=post action="/admin/status/{{o.id}}"><select name=status><option {% if o.status=='Новая' %}selected{% endif %}>Новая</option><option {% if o.status=='Подтверждена' %}selected{% endif %}>Подтверждена</option><option {% if o.status=='Выполнена' %}selected{% endif %}>Выполнена</option><option {% if o.status=='Отменена' %}selected{% endif %}>Отменена</option></select><button>Сохранить</button></form></td></tr>{% endfor %}
</tbody></table></div>{% else %}<p>Пока заявок нет. Новые заявки с сайта появятся здесь.</p>{% endif %}</html>"""

@app.get("/admin")
@admin_required
def admin():
    with db() as conn: orders=conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    return render_template_string(DASH,orders=orders)

@app.route("/admin/login", methods=["GET","POST"])
def login():
    error=None
    if request.method=="POST":
        username=request.form.get("username","")
        password=request.form.get("password","")
        if not ADMIN_PASSWORD_HASH:
            error="Не настроен ADMIN_PASSWORD_HASH в Render. Добавьте его в Environment."
        elif secrets.compare_digest(username,ADMIN_USER) and check_password_hash(ADMIN_PASSWORD_HASH,password):
            session["admin"]=True
            return redirect(request.args.get("next") or "/admin")
        else: error="Неверный логин или пароль"
    return render_template_string(LOGIN,error=error)

@app.get("/admin/logout")
def logout():
    session.clear()
    return redirect("/admin/login")

@app.post("/admin/status/<int:oid>")
@admin_required
def update_status(oid):
    status=request.form.get("status","Новая")
    if status not in ("Новая","Подтверждена","Выполнена","Отменена"): return "Bad status",400
    with db() as conn: conn.execute("UPDATE orders SET status=? WHERE id=?",(status,oid))
    return redirect("/admin")

# Set a password hash locally with: python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('YOUR_PASSWORD'))"
