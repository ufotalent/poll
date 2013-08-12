import sqlite3
from contextlib import closing
from flask import Flask, request, session, g, redirect, url_for, \
             abort, render_template, flash
import md5
import datetime


app = Flask("poll")
app.config.from_object("db");

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.execute('insert into users values (?,?)', [app.config['USERNAME'], md5.new(app.config['PASSWORD']).hexdigest()])
        db.commit()

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        uname = request.form['username']
        pas = request.form['password']
        
        cur = g.db.execute('select password from users where uname = ? ', [uname])
        data = cur.fetchall()
        if len(data)<=0:
            error = "no such user";
            return render_template('login.html', error=error)

        true_pas = data[0][0]
        if (true_pas == md5.new(pas).hexdigest()):
            session['admin'] = (uname == app.config['USERNAME'])
            session['logged_in'] = True
            session['uname'] = uname
            flash('You were logged in')
            return redirect(url_for('listuser'))
        error = "incorrect password";
        return render_template('login.html', error=error)
    return render_template('login.html', error=error)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session['admin'] == False:
        return redirect(url_for('login'))
    return render_template('admin.html')

@app.route('/adduser', methods=['GET', 'POST'])
def adduser():
    if session['admin'] == False:
        return redirect(url_for('login'))
    error = None
    if request.method == 'POST':
        if request.form['password'] == request.form['password2'] and len(request.form['password'])!= 0 and len(request.form['username'])!= 0 :
            md5pas = md5.new(request.form['password']).hexdigest()
            g.db.execute('insert into users (uname, password) values (?, ?)', [request.form['username'], md5pas] )
            g.db.commit()
            flash('User added');
        else:
            error = "invalid arguments"
    return render_template('adduser.html', error=error)


@app.route('/addcourse', methods=['GET', 'POST'])
def addcourse():
    if session['admin'] == False:
        return redirect(url_for('login'))
    error = None
    if request.method == 'POST':
        if len(request.form['name'])!= 0 :
            g.db.execute('insert into courses (name) values (?)', [request.form['name']] )
            g.db.commit()
            flash('Course added');
        else:
            error = "invalid arguments"
    return render_template('addcourse.html', error=error)

@app.route('/listuser', methods=['GET', 'POST'])
def listuser():
    if not 'logged_in' in session or session['logged_in'] == False:
        return redirect(url_for('login'))
    error = None
    cur = g.db.execute('select uname from users')
    users = [dict(uname=row[0]) for row in cur.fetchall()]
    return render_template('listuser.html', users=users)

@app.route('/listcourses', methods=['GET', 'POST'])
def listcourses():
    if not 'logged_in' in session or session['logged_in'] == False:
        return redirect(url_for('login'))
    error = None
    cur = g.db.execute('select cid, name from courses')
    courses = [dict(cid=row[0],name=row[1],score=get_score_from_id(row[0])) for row in cur.fetchall()]
    #course= [get_score_from_id(course['cid'])['score'] for course in courses]
    return render_template('listcourses.html', courses=courses)

def get_course_from_id(cid):
    cur = g.db.execute('select cid, name from courses where cid = ?',[cid]);
    courses = [dict(cid=row[0],name=row[1]) for row in cur.fetchall()]
    if len(courses) > 0:
        return courses[0]
    else:
        return None

def get_score_from_id(cid):
    cur = g.db.execute('select uname, cid, score, sid from scores where uname = ? and cid = ?', [session['uname'], cid])
    score = [dict(uname=row[0], cid=row[1], score=row[2], sid=row[3]) for row in cur.fetchall()];
    if len(score) > 0:
        return score[0]
    else:
        return None 

def get_mods_from_id(sid):
    cur = g.db.execute('select mod_value, mod_time, mod_result from transactions where sid = ? order by mod_time ASC', [sid])
    mods = [dict(mod_value=row[0], mod_time=row[1], mod_result=row[2]) for row in cur.fetchall()];
    return mods

def get_all_score_from_id(cid):
    cur = g.db.execute('select uname, cid, score from scores where cid = ? order by score DESC, uname ASC', [cid])
    allscore = [dict(uname=row[0], cid=row[1], score=row[2]) for row in cur.fetchall()];
    if len(allscore) > 0:
        return allscore
    else:
        return None 

@app.route('/course/<int:cid>')
def get_course(cid):
    if not 'logged_in' in session or session['logged_in'] == False:
        return redirect(url_for('login'))
    score = get_score_from_id(cid)
    if score == None:
        return redirect(url_for('init_course',cid=cid))
    allscore = get_all_score_from_id(cid)
    course = get_course_from_id(cid)
    mods = get_mods_from_id(score['sid'])
    print score, course, allscore

    return render_template('coursedetail.html', allscore=allscore, course=course, myscore=score, mods=mods)

@app.route('/course/alter/<int:cid>/<int:mod>')
def alter_score(cid, mod):
    if not 'logged_in' in session or session['logged_in'] == False:
        return redirect(url_for('login'))
    score = get_score_from_id(cid)
    error = None
    if score == None:
        return redirect(url_for('init_course',cid=cid))
    moddict = {
            0:-2,
            1:-1,
            2:1,
            3:2
            }
    if mod in moddict:
        g.db.execute('update scores set score=score+? where sid=? ', [moddict[mod], score['sid']])
        g.db.execute('insert into transactions (sid, mod_value, mod_time, mod_result) values (?,?,?,?)',[score['sid'], moddict[mod], datetime.datetime.now(), score['score']+moddict[mod] ])
        g.db.commit()
        flash('score mod success!');
    return redirect(url_for('get_course',cid=cid))

    
@app.route('/course/init/<int:cid>', methods=['GET', 'POST'])
def init_course(cid):
    if session['logged_in'] == False:
        return redirect(url_for('login'))
    if get_score_from_id(cid) != None:
        return redirect(url_for('get_course',cid=cid));

    error = None
    if request.method == 'POST':
        if len(request.form['score'])!= 0 :
            g.db.execute('insert into scores (uname, cid, score) values (?, ?, ?)', [session['uname'], cid, int(request.form['score'])] )
            score = get_score_from_id(cid);
            g.db.execute('insert into transactions (sid, mod_value, mod_time, mod_result) values (?,?,?,?)',[score['sid'], int(request.form['score']), datetime.datetime.now(), int(request.form['score']) ])
            g.db.commit()
            return redirect(url_for('get_course',cid=cid))
        else:
            error = "invalid arguments"
    return render_template('initcourse.html', error=error, course = get_course_from_id(cid));

@app.route('/')
def root():
    return redirect(url_for('listcourses'));

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('admin', None)
    flash('You were logged out')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run()
