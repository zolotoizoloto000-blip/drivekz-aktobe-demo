from fastapi import FastAPI, Request, Query, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import sqlite3, os, shutil, uuid
from datetime import datetime, date, timedelta
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'drivekz.db')
UPLOAD_DIR = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title='Автопрокат Актобе')
app.add_middleware(SessionMiddleware, secret_key='drivekz-demo-secret-change-in-production', max_age=60*60*24*30)
app.mount('/static', StaticFiles(directory=os.path.join(BASE_DIR, 'static')), name='static')
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, 'templates'))

SEED_CARS = [
 {'name':'Toyota Camry 70','city':'Актобе','price':25000,'class':'Бизнес','body':'Седан','gearbox':'Автомат','fuel':'Бензин','seats':5,'year':2024,'deposit':100000,'rating':4.9,'image':'img/camry.svg','badge':'Популярный','features':'Климат-контроль|Apple CarPlay|Камера 360°|Круиз-контроль'},
 {'name':'Hyundai Tucson','city':'Актобе','price':29000,'class':'Комфорт','body':'Кроссовер','gearbox':'Автомат','fuel':'Бензин','seats':5,'year':2023,'deposit':120000,'rating':4.8,'image':'img/tucson.svg','badge':'Выгодно','features':'Подогрев сидений|CarPlay|Парктроники|Круиз-контроль'},
 {'name':'Toyota Land Cruiser 300','city':'Актобе','price':65000,'class':'Премиум','body':'Внедорожник','gearbox':'Автомат','fuel':'Бензин','seats':7,'year':2024,'deposit':300000,'rating':5.0,'image':'img/lc300.svg','badge':'Premium','features':'7 мест|Камера 360°|Вентиляция сидений|Полный привод'},
 {'name':'Kia K5','city':'Актобе','price':22000,'class':'Комфорт','body':'Седан','gearbox':'Автомат','fuel':'Бензин','seats':5,'year':2023,'deposit':90000,'rating':4.7,'image':'img/k5.svg','badge':'','features':'Климат-контроль|Bluetooth|Камера заднего вида|Подогрев сидений'},
 {'name':'BMW X5','city':'Актобе','price':72000,'class':'Премиум','body':'Кроссовер','gearbox':'Автомат','fuel':'Бензин','seats':5,'year':2024,'deposit':350000,'rating':4.9,'image':'img/x5.svg','badge':'Premium','features':'Панорама|Камера 360°|Harman Kardon|Полный привод'},
 {'name':'Chevrolet Cobalt','city':'Актобе','price':15000,'class':'Эконом','body':'Седан','gearbox':'Автомат','fuel':'Бензин','seats':5,'year':2022,'deposit':60000,'rating':4.6,'image':'img/cobalt.svg','badge':'Лучшая цена','features':'Кондиционер|Bluetooth|USB|Экономичный расход'},
]

EXTRA_PRICES = {'Детское кресло':3000,'Дополнительный водитель':5000,'Доставка авто':4000,'Полная страховка':7000}
BOOKING_STATUSES = ['Новая','Ожидает оплату','Подтверждена','Машина выдана','Завершена','Отменена']
CAR_STATUSES = ['Доступен','На ремонте','Недоступен']


def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def has_column(conn, table, column):
    return any(r['name'] == column for r in conn.execute(f'PRAGMA table_info({table})').fetchall())


def init_db():
    c = db()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS bookings(
      id INTEGER PRIMARY KEY AUTOINCREMENT, car_id INTEGER, car_name TEXT, city TEXT,
      pickup_date TEXT, pickup_time TEXT, return_date TEXT, return_time TEXT,
      customer_name TEXT, phone TEXT, email TEXT, pickup_location TEXT, extras TEXT,
      total INTEGER, status TEXT DEFAULT 'Новая', source TEXT DEFAULT 'Сайт', created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS notifications(
      id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER, text TEXT,
      is_read INTEGER DEFAULT 0, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS cars(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, city TEXT, price INTEGER, class TEXT,
      body TEXT, gearbox TEXT, fuel TEXT, seats INTEGER, year INTEGER, deposit INTEGER,
      rating REAL DEFAULT 5, image TEXT, badge TEXT, features TEXT, status TEXT DEFAULT 'Доступен',
      hidden INTEGER DEFAULT 0, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT UNIQUE, name TEXT, email TEXT,
      city TEXT, birthdate TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS documents(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, doc_type TEXT, filename TEXT,
      path TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS payments(
      id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER, amount INTEGER,
      method TEXT, status TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS promos(
      id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, discount INTEGER,
      kind TEXT DEFAULT 'percent', active INTEGER DEFAULT 1, expires_at TEXT, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS settings(
      key TEXT PRIMARY KEY, value TEXT
    );
    ''')
    if not has_column(c, 'bookings', 'user_id'):
        c.execute('ALTER TABLE bookings ADD COLUMN user_id INTEGER')
    if not has_column(c, 'bookings', 'promo_code'):
        c.execute('ALTER TABLE bookings ADD COLUMN promo_code TEXT')
    if c.execute('SELECT COUNT(*) c FROM cars').fetchone()['c'] == 0:
        for car in SEED_CARS:
            c.execute('''INSERT INTO cars(name,city,price,class,body,gearbox,fuel,seats,year,deposit,rating,image,badge,features,status,hidden,created_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                      (car['name'],car['city'],car['price'],car['class'],car['body'],car['gearbox'],car['fuel'],car['seats'],car['year'],car['deposit'],car['rating'],car['image'],car['badge'],car['features'],'Доступен',0,datetime.now().strftime('%Y-%m-%d %H:%M')))
    defaults = {'company_name':'Автопрокат Актобе','phone':'+7 775 430 63 20','whatsapp':'+7 775 430 63 20','support_email':'hello@drive.kz','currency':'₸','booking_mode':'manual','reminder_minutes':'10'}
    for k,v in defaults.items(): c.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)',(k,v))
    c.commit(); c.close()

init_db()


def rows_to_cars(rows):
    out=[]
    for r in rows:
        d=dict(r); d['features']=[x for x in (d.get('features') or '').split('|') if x]; d['available']=d.get('status')=='Доступен' and not d.get('hidden'); out.append(d)
    return out


def all_cars(include_hidden=False):
    c=db(); q='SELECT * FROM cars' if include_hidden else 'SELECT * FROM cars WHERE hidden=0'; rows=c.execute(q+' ORDER BY id').fetchall(); c.close(); return rows_to_cars(rows)


def car_by_id(car_id):
    c=db(); r=c.execute('SELECT * FROM cars WHERE id=?',(car_id,)).fetchone(); c.close(); return rows_to_cars([r])[0] if r else None


def unread_count():
    c=db(); n=c.execute('SELECT COUNT(*) c FROM notifications WHERE is_read=0').fetchone()['c']; c.close(); return n


def current_user(request):
    uid=request.session.get('user_id')
    if not uid: return None
    c=db(); u=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone(); c.close(); return dict(u) if u else None


def settings_dict():
    c=db(); s={r['key']:r['value'] for r in c.execute('SELECT * FROM settings').fetchall()}; c.close(); return s


def ctx(request, **kw):
    return {'request':request,'unread_notifications':unread_count(),'user':current_user(request),'settings':settings_dict(),**kw}


def is_busy(car_id, start, end, ignore_booking_id=None):
    if not start or not end: return False
    c=db(); sql="SELECT COUNT(*) c FROM bookings WHERE car_id=? AND status != 'Отменена' AND NOT (return_date <= ? OR pickup_date >= ?)"; args=[car_id,start,end]
    if ignore_booking_id: sql += ' AND id != ?'; args.append(ignore_booking_id)
    n=c.execute(sql,args).fetchone()['c']; c.close(); return n>0


def add_notification(text, booking_id=None):
    c=db(); c.execute('INSERT INTO notifications(booking_id,text,is_read,created_at) VALUES(?,?,0,?)',(booking_id,text,datetime.now().strftime('%Y-%m-%d %H:%M'))); c.commit(); c.close()


def booking_days(start,end):
    try: return max((datetime.strptime(end,'%Y-%m-%d')-datetime.strptime(start,'%Y-%m-%d')).days,1)
    except: return 1


def resolve_user_id(phone, name='', email=''):
    if not phone: return None
    c=db(); u=c.execute('SELECT * FROM users WHERE phone=?',(phone,)).fetchone()
    if u: uid=u['id']; c.execute('UPDATE users SET name=COALESCE(NULLIF(?,\'\'),name), email=COALESCE(NULLIF(?,\'\'),email) WHERE id=?',(name,email,uid))
    else:
        cur=c.execute('INSERT INTO users(phone,name,email,created_at) VALUES(?,?,?,?)',(phone,name,email,datetime.now().strftime('%Y-%m-%d %H:%M'))); uid=cur.lastrowid
    c.commit(); c.close(); return uid


@app.get('/', response_class=HTMLResponse, name='home')
def home(request:Request): return templates.TemplateResponse(request=request,name='home.html',context=ctx(request,cars=all_cars()[:3]))

@app.get('/catalog', response_class=HTMLResponse, name='catalog')
def catalog(request:Request,city:str='',min_price:int=0,max_price:int=100000,car_class:str=Query('',alias='class'),gearbox:str='',body:str='',fuel:str='',seats:int=0,no_deposit:int=0,q:str='',sort:str='popular',pickup:str='',return_date:str=Query('',alias='return')):
    cars=[x for x in all_cars() if x['status']=='Доступен']
    if city: cars=[x for x in cars if x['city']==city]
    if min_price: cars=[x for x in cars if x['price']>=min_price]
    if max_price: cars=[x for x in cars if x['price']<=max_price]
    if car_class: cars=[x for x in cars if x['class']==car_class]
    if gearbox: cars=[x for x in cars if x['gearbox']==gearbox]
    if body: cars=[x for x in cars if x['body']==body]
    if fuel: cars=[x for x in cars if x['fuel']==fuel]
    if seats: cars=[x for x in cars if x['seats']>=seats]
    if no_deposit: cars=[x for x in cars if x['deposit']<=100000]
    if q:
        needle=q.lower().strip(); cars=[x for x in cars if any(needle in str(x.get(k,'')).lower() for k in ['name','class','body','city'])]
    if pickup and return_date: cars=[x for x in cars if not is_busy(x['id'],pickup,return_date)]
    if sort=='price_asc': cars.sort(key=lambda x:x['price'])
    elif sort=='price_desc': cars.sort(key=lambda x:x['price'],reverse=True)
    elif sort=='rating': cars.sort(key=lambda x:x['rating'],reverse=True)
    else: cars.sort(key=lambda x:(x['badge']!='Популярный',-x['rating']))
    return templates.TemplateResponse(request=request,name='catalog.html',context=ctx(request,cars=cars,city=city,min_price=min_price,max_price=max_price,car_class=car_class,gearbox=gearbox,body=body,fuel=fuel,seats=seats,no_deposit=no_deposit,q=q,sort=sort,pickup=pickup,return_date=return_date))

@app.get('/car/{car_id}', response_class=HTMLResponse, name='car_detail')
def car_detail(request:Request,car_id:int):
    car=car_by_id(car_id)
    if not car or car['hidden']: return HTMLResponse('Автомобиль не найден',404)
    return templates.TemplateResponse(request=request,name='car_detail.html',context=ctx(request,car=car))

@app.get('/favorites', response_class=HTMLResponse, name='favorites')
def favorites(request:Request): return templates.TemplateResponse(request=request,name='favorites.html',context=ctx(request,cars=all_cars()))

# --- Demo authentication ---
@app.get('/login', response_class=HTMLResponse, name='login')
def login(request:Request): return templates.TemplateResponse(request=request,name='login.html',context=ctx(request,step='phone',phone=''))

@app.post('/login', response_class=HTMLResponse, name='login_phone')
async def login_phone(request:Request):
    f=await request.form(); phone=(f.get('phone') or '').strip()
    if not phone: return templates.TemplateResponse(request=request,name='login.html',context=ctx(request,step='phone',phone='',error='Введите номер телефона'),status_code=400)
    request.session['login_phone']=phone; request.session['otp']='1111'
    return templates.TemplateResponse(request=request,name='login.html',context=ctx(request,step='code',phone=phone,demo_code='1111'))

@app.post('/login/verify', name='login_verify')
async def login_verify(request:Request):
    f=await request.form(); code=(f.get('code') or '').strip(); phone=request.session.get('login_phone')
    if not phone or code!=request.session.get('otp'):
        return templates.TemplateResponse(request=request,name='login.html',context=ctx(request,step='code',phone=phone or '',demo_code='1111',error='Неверный код. Для демо используйте 1111'),status_code=400)
    uid=resolve_user_id(phone, f.get('name') or 'Клиент', f.get('email') or '')
    request.session['user_id']=uid; request.session.pop('otp',None); return RedirectResponse('/profile',303)

@app.post('/login/oauth/{provider}', name='demo_oauth')
def demo_oauth(request:Request,provider:str):
    provider=provider.capitalize(); phone=f'demo-{provider.lower()}@drive.kz'; uid=resolve_user_id(phone,f'{provider} User',f'{provider.lower()}@example.com'); request.session['user_id']=uid; return RedirectResponse('/profile',303)

@app.get('/logout', name='logout')
def logout(request:Request): request.session.clear(); return RedirectResponse('/',303)

@app.get('/profile', response_class=HTMLResponse, name='profile')
def profile(request:Request,section:str='bookings',status:str=''):
    user=current_user(request)
    c=db()
    if user:
        q='SELECT * FROM bookings WHERE user_id=?'; args=[user['id']]
        if status: q+=' AND status=?'; args.append(status)
        bookings=c.execute(q+' ORDER BY id DESC',args).fetchall(); docs=c.execute('SELECT * FROM documents WHERE user_id=? ORDER BY id DESC',(user['id'],)).fetchall()
    else:
        bookings=c.execute('SELECT * FROM bookings ORDER BY id DESC LIMIT 8').fetchall(); docs=[]
    promos=c.execute('SELECT * FROM promos WHERE active=1 ORDER BY id DESC').fetchall(); c.close()
    return templates.TemplateResponse(request=request,name='profile.html',context=ctx(request,bookings=bookings,documents=docs,promos=promos,section=section,status_filter=status))

@app.post('/profile/settings', name='profile_settings')
async def profile_settings(request:Request):
    u=current_user(request)
    if not u: return RedirectResponse('/login',303)
    f=await request.form(); c=db(); c.execute('UPDATE users SET name=?,email=?,city=?,birthdate=? WHERE id=?',(f.get('name'),f.get('email'),f.get('city'),f.get('birthdate'),u['id'])); c.commit(); c.close(); return RedirectResponse('/profile?section=settings&saved=1',303)

@app.post('/profile/document', name='profile_document')
async def profile_document(request:Request, doc_type:str=Form(...), document:UploadFile=File(...)):
    u=current_user(request)
    if not u: return RedirectResponse('/login',303)
    ext=os.path.splitext(document.filename or '')[1][:10]; filename=f'{uuid.uuid4().hex}{ext}'; dest=os.path.join(UPLOAD_DIR,filename)
    with open(dest,'wb') as out: shutil.copyfileobj(document.file,out)
    c=db(); c.execute('INSERT INTO documents(user_id,doc_type,filename,path,created_at) VALUES(?,?,?,?,?)',(u['id'],doc_type,document.filename,f'uploads/{filename}',datetime.now().strftime('%Y-%m-%d %H:%M'))); c.commit(); c.close(); return RedirectResponse('/profile?section=documents',303)

@app.post('/profile/booking/{booking_id}/cancel', name='cancel_booking')
def cancel_booking(request:Request,booking_id:int):
    u=current_user(request); c=db(); b=c.execute('SELECT * FROM bookings WHERE id=?',(booking_id,)).fetchone()
    if b and (not u or b['user_id']==u['id']): c.execute("UPDATE bookings SET status='Отменена' WHERE id=?",(booking_id,)); c.commit(); add_notification(f'Клиент отменил бронь #{booking_id}',booking_id)
    c.close(); return RedirectResponse('/profile',303)

# --- Booking ---
@app.get('/booking/{car_id}', response_class=HTMLResponse, name='booking')
def booking_get(request:Request,car_id:int,pickup:str='',return_date:str=Query('',alias='return'),promo:str=''):
    car=car_by_id(car_id)
    if not car or car['hidden'] or car['status']!='Доступен': return HTMLResponse('Автомобиль сейчас недоступен',404)
    return templates.TemplateResponse(request=request,name='booking.html',context=ctx(request,car=car,pickup=pickup,return_date=return_date,promo=promo,extra_prices=EXTRA_PRICES))

@app.post('/booking/{car_id}', name='booking_post')
async def booking_post(request:Request,car_id:int):
    car=car_by_id(car_id)
    if not car or car['status']!='Доступен': return HTMLResponse('Автомобиль недоступен',409)
    f=await request.form(); pd=f.get('pickup_date'); rd=f.get('return_date')
    if not pd or not rd or rd<=pd: return HTMLResponse('Проверьте даты аренды',400)
    if is_busy(car_id,pd,rd): return HTMLResponse('Автомобиль уже занят на выбранные даты. Вернитесь назад и выберите другой период.',409)
    days=booking_days(pd,rd); extras_list=f.getlist('extras'); extras=', '.join(extras_list); extras_price=sum(EXTRA_PRICES.get(x,0) for x in extras_list); subtotal=car['price']*days+extras_price
    promo_code=(f.get('promo_code') or '').strip().upper(); discount=0
    if promo_code:
        c=db(); p=c.execute("SELECT * FROM promos WHERE code=? AND active=1 AND (expires_at IS NULL OR expires_at='' OR expires_at>=?)",(promo_code,date.today().isoformat())).fetchone(); c.close()
        if p: discount=(subtotal*p['discount']//100) if p['kind']=='percent' else min(subtotal,p['discount'])
    total=max(0,subtotal-discount); uid=resolve_user_id(f.get('phone'),f.get('customer_name'),f.get('email',''))
    c=db(); cur=c.execute('''INSERT INTO bookings(car_id,car_name,city,pickup_date,pickup_time,return_date,return_time,customer_name,phone,email,pickup_location,extras,total,status,source,created_at,user_id,promo_code)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(car['id'],car['name'],car['city'],pd,f.get('pickup_time','10:00'),rd,f.get('return_time','10:00'),f.get('customer_name'),f.get('phone'),f.get('email',''),f.get('pickup_location','Офис проката'),extras,total,'Новая','Сайт',datetime.now().strftime('%Y-%m-%d %H:%M'),uid,promo_code)); bid=cur.lastrowid; c.commit(); c.close()
    add_notification(f'Новая бронь #{bid}: {car["name"]} — {f.get("customer_name")}, {total:,} ₸'.replace(',',' '),bid)
    return RedirectResponse(f'/booking-success/{bid}',303)

@app.get('/booking-success/{booking_id}', response_class=HTMLResponse, name='booking_success')
def booking_success(request:Request,booking_id:int):
    c=db(); b=c.execute('SELECT * FROM bookings WHERE id=?',(booking_id,)).fetchone(); c.close()
    if not b:return HTMLResponse('Бронь не найдена',404)
    return templates.TemplateResponse(request=request,name='booking_success.html',context=ctx(request,booking=b))

# --- Admin ---
@app.get('/admin', response_class=HTMLResponse, name='admin_dashboard')
def admin_dashboard(request:Request):
    c=db(); bookings=c.execute('SELECT * FROM bookings ORDER BY id DESC LIMIT 8').fetchall(); t=c.execute("SELECT COUNT(*) c,COALESCE(SUM(CASE WHEN status!='Отменена' THEN total ELSE 0 END),0) s FROM bookings").fetchone(); active=c.execute("SELECT COUNT(*) c FROM bookings WHERE status IN ('Подтверждена','Машина выдана')").fetchone()['c']; today_count=c.execute('SELECT COUNT(*) c FROM bookings WHERE substr(created_at,1,10)=?',(date.today().isoformat(),)).fetchone()['c']; c.close(); cars=all_cars(True)
    return templates.TemplateResponse(request=request,name='admin_dashboard.html',context=ctx(request,bookings=bookings,stats={'bookings':t['c'],'revenue':t['s'],'active':active,'cars':len(cars),'today':today_count},cars=cars))

@app.get('/admin/bookings', response_class=HTMLResponse, name='admin_bookings')
def admin_bookings(request:Request,status:str='',q:str=''):
    c=db(); sql='SELECT * FROM bookings WHERE 1=1'; args=[]
    if status: sql+=' AND status=?'; args.append(status)
    if q: sql+=' AND (customer_name LIKE ? OR phone LIKE ? OR car_name LIKE ? OR CAST(id AS TEXT) LIKE ?)'; args.extend([f'%{q}%']*4)
    bookings=c.execute(sql+' ORDER BY id DESC',args).fetchall(); c.close(); return templates.TemplateResponse(request=request,name='admin_bookings.html',context=ctx(request,bookings=bookings,status_filter=status,q=q,statuses=BOOKING_STATUSES))

@app.post('/admin/booking/{booking_id}/status', name='update_booking_status')
async def update_booking_status(request:Request,booking_id:int):
    f=await request.form(); status=f.get('status'); c=db(); c.execute('UPDATE bookings SET status=? WHERE id=?',(status,booking_id)); c.commit(); c.close(); add_notification(f'Статус брони #{booking_id}: {status}',booking_id); return RedirectResponse(request.headers.get('referer','/admin/bookings'),303)

@app.get('/admin/new-booking', response_class=HTMLResponse, name='admin_new_booking')
def admin_new_booking_get(request:Request): return templates.TemplateResponse(request=request,name='admin_new_booking.html',context=ctx(request,cars=[x for x in all_cars() if x['status']=='Доступен']))

@app.post('/admin/new-booking', name='admin_new_booking_post')
async def admin_new_booking_post(request:Request):
    f=await request.form(); car=car_by_id(int(f.get('car_id'))); pd=f.get('pickup_date'); rd=f.get('return_date')
    if not car or not pd or not rd or rd<=pd: return HTMLResponse('Проверьте автомобиль и даты',400)
    if is_busy(car['id'],pd,rd): return HTMLResponse('Этот автомобиль уже занят на выбранный период.',409)
    days=booking_days(pd,rd); total=int(f.get('total') or car['price']*days); uid=resolve_user_id(f.get('phone'),f.get('customer_name'),f.get('email',''))
    c=db(); cur=c.execute('''INSERT INTO bookings(car_id,car_name,city,pickup_date,pickup_time,return_date,return_time,customer_name,phone,email,pickup_location,extras,total,status,source,created_at,user_id)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(car['id'],car['name'],car['city'],pd,f.get('pickup_time','10:00'),rd,f.get('return_time','10:00'),f.get('customer_name'),f.get('phone'),f.get('email',''),f.get('pickup_location','Офис проката'),f.get('extras',''),total,'Подтверждена','Менеджер',datetime.now().strftime('%Y-%m-%d %H:%M'),uid)); bid=cur.lastrowid; c.commit(); c.close(); add_notification(f'Менеджер создал бронь #{bid}: {car["name"]}',bid); return RedirectResponse('/admin/bookings',303)

@app.get('/admin/cars', response_class=HTMLResponse, name='admin_cars')
def admin_cars(request:Request): return templates.TemplateResponse(request=request,name='admin_cars.html',context=ctx(request,cars=all_cars(True)))

@app.get('/admin/cars/new', response_class=HTMLResponse, name='admin_car_new')
def admin_car_new(request:Request): return templates.TemplateResponse(request=request,name='admin_car_form.html',context=ctx(request,car=None,statuses=CAR_STATUSES))

@app.post('/admin/cars/new', name='admin_car_create')
async def admin_car_create(request:Request):
    f=await request.form(); image=f.get('image') or 'img/camry.svg'; c=db(); c.execute('''INSERT INTO cars(name,city,price,class,body,gearbox,fuel,seats,year,deposit,rating,image,badge,features,status,hidden,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(f.get('name'),f.get('city'),int(f.get('price') or 0),f.get('class'),f.get('body'),f.get('gearbox'),f.get('fuel'),int(f.get('seats') or 5),int(f.get('year') or date.today().year),int(f.get('deposit') or 0),float(f.get('rating') or 5),image,f.get('badge',''),(f.get('features') or '').replace(',','|'),f.get('status','Доступен'),0,datetime.now().strftime('%Y-%m-%d %H:%M'))); c.commit(); c.close(); return RedirectResponse('/admin/cars',303)

@app.get('/admin/cars/{car_id}/edit', response_class=HTMLResponse, name='admin_car_edit')
def admin_car_edit(request:Request,car_id:int):
    car=car_by_id(car_id)
    if not car:return HTMLResponse('Авто не найдено',404)
    return templates.TemplateResponse(request=request,name='admin_car_form.html',context=ctx(request,car=car,statuses=CAR_STATUSES))

@app.post('/admin/cars/{car_id}/edit', name='admin_car_update')
async def admin_car_update(request:Request,car_id:int):
    f=await request.form(); c=db(); c.execute('''UPDATE cars SET name=?,city=?,price=?,class=?,body=?,gearbox=?,fuel=?,seats=?,year=?,deposit=?,rating=?,image=?,badge=?,features=?,status=? WHERE id=?''',(f.get('name'),f.get('city'),int(f.get('price') or 0),f.get('class'),f.get('body'),f.get('gearbox'),f.get('fuel'),int(f.get('seats') or 5),int(f.get('year') or date.today().year),int(f.get('deposit') or 0),float(f.get('rating') or 5),f.get('image') or 'img/camry.svg',f.get('badge',''),(f.get('features') or '').replace(',','|'),f.get('status','Доступен'),car_id)); c.commit(); c.close(); return RedirectResponse('/admin/cars',303)

@app.post('/admin/cars/{car_id}/action', name='admin_car_action')
async def admin_car_action(request:Request,car_id:int):
    f=await request.form(); action=f.get('action'); c=db()
    if action=='repair': c.execute("UPDATE cars SET status='На ремонте' WHERE id=?",(car_id,))
    elif action=='available': c.execute("UPDATE cars SET status='Доступен' WHERE id=?",(car_id,))
    elif action=='toggle_hidden': c.execute('UPDATE cars SET hidden=CASE hidden WHEN 1 THEN 0 ELSE 1 END WHERE id=?',(car_id,))
    c.commit(); c.close(); return RedirectResponse('/admin/cars',303)

@app.get('/admin/calendar', response_class=HTMLResponse, name='admin_calendar')
def admin_calendar(request:Request,start:str=''):
    try: start_date=datetime.strptime(start,'%Y-%m-%d').date() if start else date.today()
    except: start_date=date.today()
    dates=[start_date+timedelta(days=i) for i in range(14)]; end=(dates[-1]+timedelta(days=1)).isoformat(); c=db(); bookings=c.execute("SELECT * FROM bookings WHERE status!='Отменена' AND NOT (return_date<=? OR pickup_date>=?) ORDER BY pickup_date",(start_date.isoformat(),end)).fetchall(); c.close()
    occupancy=defaultdict(dict)
    for b in bookings:
        ps=datetime.strptime(b['pickup_date'],'%Y-%m-%d').date(); re=datetime.strptime(b['return_date'],'%Y-%m-%d').date()
        for d in dates:
            if ps<=d<re: occupancy[b['car_id']][d.isoformat()]=dict(b)
    return templates.TemplateResponse(request=request,name='admin_calendar.html',context=ctx(request,cars=all_cars(True),bookings=bookings,dates=dates,occupancy=occupancy,start_date=start_date,prev=(start_date-timedelta(days=14)).isoformat(),next=(start_date+timedelta(days=14)).isoformat()))

@app.get('/admin/clients', response_class=HTMLResponse, name='admin_clients')
def admin_clients(request:Request,q:str=''):
    c=db(); sql='''SELECT u.*, COUNT(b.id) bookings_count, COALESCE(SUM(CASE WHEN b.status!='Отменена' THEN b.total ELSE 0 END),0) spent FROM users u LEFT JOIN bookings b ON b.user_id=u.id'''; args=[]
    if q: sql+=' WHERE u.name LIKE ? OR u.phone LIKE ? OR u.email LIKE ?'; args=[f'%{q}%']*3
    sql+=' GROUP BY u.id ORDER BY u.id DESC'; clients=c.execute(sql,args).fetchall(); c.close(); return templates.TemplateResponse(request=request,name='admin_clients.html',context=ctx(request,clients=clients,q=q))

@app.get('/admin/clients/{user_id}', response_class=HTMLResponse, name='admin_client_detail')
def admin_client_detail(request:Request,user_id:int):
    c=db(); u=c.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone(); bookings=c.execute('SELECT * FROM bookings WHERE user_id=? ORDER BY id DESC',(user_id,)).fetchall(); docs=c.execute('SELECT * FROM documents WHERE user_id=? ORDER BY id DESC',(user_id,)).fetchall(); c.close()
    if not u:return HTMLResponse('Клиент не найден',404)
    return templates.TemplateResponse(request=request,name='admin_client_detail.html',context=ctx(request,client=u,bookings=bookings,documents=docs))

@app.get('/admin/payments', response_class=HTMLResponse, name='admin_payments')
def admin_payments(request:Request):
    c=db(); payments=c.execute('''SELECT p.*,b.car_name,b.customer_name FROM payments p LEFT JOIN bookings b ON b.id=p.booking_id ORDER BY p.id DESC''').fetchall(); bookings=c.execute("SELECT * FROM bookings WHERE status!='Отменена' ORDER BY id DESC").fetchall(); c.close(); return templates.TemplateResponse(request=request,name='admin_payments.html',context=ctx(request,payments=payments,bookings=bookings))

@app.post('/admin/payments', name='admin_payment_create')
async def admin_payment_create(request:Request):
    f=await request.form(); bid=int(f.get('booking_id')); amount=int(f.get('amount') or 0); method=f.get('method'); c=db(); c.execute('INSERT INTO payments(booking_id,amount,method,status,created_at) VALUES(?,?,?,?,?)',(bid,amount,method,'Оплачено',datetime.now().strftime('%Y-%m-%d %H:%M'))); c.execute("UPDATE bookings SET status=CASE WHEN status='Новая' OR status='Ожидает оплату' THEN 'Подтверждена' ELSE status END WHERE id=?",(bid,)); c.commit(); c.close(); add_notification(f'Получена оплата по брони #{bid}: {amount:,} ₸'.replace(',',' '),bid); return RedirectResponse('/admin/payments',303)

@app.post('/admin/payments/{payment_id}/refund', name='admin_payment_refund')
def admin_payment_refund(payment_id:int):
    c=db(); c.execute("UPDATE payments SET status='Возврат' WHERE id=?",(payment_id,)); c.commit(); c.close(); return RedirectResponse('/admin/payments',303)

@app.get('/admin/promos', response_class=HTMLResponse, name='admin_promos')
def admin_promos(request:Request):
    c=db(); promos=c.execute('SELECT * FROM promos ORDER BY id DESC').fetchall(); c.close(); return templates.TemplateResponse(request=request,name='admin_promos.html',context=ctx(request,promos=promos))

@app.post('/admin/promos', name='admin_promo_create')
async def admin_promo_create(request:Request):
    f=await request.form(); c=db()
    try: c.execute('INSERT INTO promos(code,discount,kind,active,expires_at,created_at) VALUES(?,?,?,?,?,?)',((f.get('code') or '').upper(),int(f.get('discount') or 0),f.get('kind','percent'),1,f.get('expires_at',''),datetime.now().strftime('%Y-%m-%d %H:%M'))); c.commit()
    except sqlite3.IntegrityError: pass
    c.close(); return RedirectResponse('/admin/promos',303)

@app.post('/admin/promos/{promo_id}/toggle', name='admin_promo_toggle')
def admin_promo_toggle(promo_id:int):
    c=db(); c.execute('UPDATE promos SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?',(promo_id,)); c.commit(); c.close(); return RedirectResponse('/admin/promos',303)

@app.get('/admin/analytics', response_class=HTMLResponse, name='admin_analytics')
def admin_analytics(request:Request):
    c=db(); month_rows=c.execute("SELECT substr(created_at,1,7) m,COUNT(*) n,COALESCE(SUM(CASE WHEN status!='Отменена' THEN total ELSE 0 END),0) revenue FROM bookings GROUP BY m ORDER BY m DESC LIMIT 6").fetchall(); car_rows=c.execute("SELECT car_name,COUNT(*) n,COALESCE(SUM(CASE WHEN status!='Отменена' THEN total ELSE 0 END),0) revenue FROM bookings GROUP BY car_name ORDER BY revenue DESC LIMIT 8").fetchall(); source_rows=c.execute("SELECT source,COUNT(*) n FROM bookings GROUP BY source ORDER BY n DESC").fetchall(); c.close(); return templates.TemplateResponse(request=request,name='admin_analytics.html',context=ctx(request,months=list(reversed(month_rows)),car_stats=car_rows,source_stats=source_rows))

@app.get('/admin/settings', response_class=HTMLResponse, name='admin_settings')
def admin_settings(request:Request): return templates.TemplateResponse(request=request,name='admin_settings.html',context=ctx(request,current=settings_dict()))

@app.post('/admin/settings', name='admin_settings_save')
async def admin_settings_save(request:Request):
    f=await request.form(); c=db()
    for k in ['company_name','phone','whatsapp','support_email','currency','booking_mode','reminder_minutes']:
        if k in f: c.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,f.get(k)))
    c.commit(); c.close(); return RedirectResponse('/admin/settings?saved=1',303)

@app.get('/admin/notifications', response_class=HTMLResponse, name='admin_notifications')
def admin_notifications(request:Request):
    c=db(); notes=c.execute('SELECT * FROM notifications ORDER BY id DESC LIMIT 100').fetchall(); c.execute('UPDATE notifications SET is_read=1'); c.commit(); c.close(); return templates.TemplateResponse(request=request,name='admin_notifications.html',context=ctx(request,notes=notes))

@app.get('/admin/search', response_class=HTMLResponse, name='admin_search')
def admin_search(request:Request,q:str=''):
    c=db(); bookings=c.execute("SELECT * FROM bookings WHERE customer_name LIKE ? OR phone LIKE ? OR car_name LIKE ? OR CAST(id AS TEXT) LIKE ? ORDER BY id DESC LIMIT 20",[f'%{q}%']*4).fetchall() if q else []; clients=c.execute("SELECT * FROM users WHERE name LIKE ? OR phone LIKE ? OR email LIKE ? ORDER BY id DESC LIMIT 20",[f'%{q}%']*3).fetchall() if q else []; cars=c.execute("SELECT * FROM cars WHERE name LIKE ? OR city LIKE ? ORDER BY id DESC LIMIT 20",[f'%{q}%']*2).fetchall() if q else []; c.close(); return templates.TemplateResponse(request=request,name='admin_search.html',context=ctx(request,q=q,bookings=bookings,clients=clients,cars=cars))

@app.get('/api/check-availability', name='check_availability')
def check_availability(car_id:int,start:str,end:str):
    car=car_by_id(car_id); return JSONResponse({'available':bool(car and car['status']=='Доступен' and not car['hidden'] and not is_busy(car_id,start,end))})

@app.get('/api/promo', name='check_promo')
def check_promo(code:str,amount:int=0):
    c=db(); p=c.execute("SELECT * FROM promos WHERE code=? AND active=1 AND (expires_at IS NULL OR expires_at='' OR expires_at>=?)",(code.upper(),date.today().isoformat())).fetchone(); c.close()
    if not p:return JSONResponse({'valid':False})
    discount=(amount*p['discount']//100) if p['kind']=='percent' else min(amount,p['discount']); return JSONResponse({'valid':True,'discount':discount,'label':f"-{p['discount']}%" if p['kind']=='percent' else f"-{p['discount']} ₸"})

@app.get('/about', response_class=HTMLResponse, name='about')
def about(request:Request):return templates.TemplateResponse(request=request,name='simple.html',context=ctx(request,title='О сервисе',body='Современный сервис аренды автомобилей в Актобе с прозрачными ценами, онлайн-бронированием и удобной связью через WhatsApp.'))
@app.get('/terms', response_class=HTMLResponse, name='terms')
def terms(request:Request):return templates.TemplateResponse(request=request,name='simple.html',context=ctx(request,title='Условия аренды',body='Минимальный возраст, стаж, залог, лимит пробега, правила возврата и страхования настраиваются владельцем автопроката в админ-панели.'))
@app.get('/faq', response_class=HTMLResponse, name='faq')
def faq(request:Request):return templates.TemplateResponse(request=request,name='faq.html',context=ctx(request))

if __name__=='__main__':
    import uvicorn; uvicorn.run(app,host='0.0.0.0',port=5000)
