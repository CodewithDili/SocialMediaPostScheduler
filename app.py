from flask import Flask, request, redirect, url_for, render_template, session, flash
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
import requests
from werkzeug.security import generate_password_hash, check_password_hash
import apscheduler.events

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scheduler.db'
db = SQLAlchemy(app)
scheduler = BackgroundScheduler()
scheduler.start()

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ScheduledPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    content = db.Column(db.String(280), nullable=False)
    post_time = db.Column(db.DateTime, nullable=False)
    user = db.relationship('User', backref=db.backref('posts', lazy=True))

# Routes
@app.route('/')
def index():
    try:
        if 'user_id' not in session:
            return redirect(url_for('login'))
        posts = ScheduledPost.query.filter_by(user_id=session['user_id']).all()
        return render_template('index.html', posts=posts)
    except Exception as e:
        print(f'Error rendering index template: {e}')
        return "An error occurred while loading the page.", 500

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            flash('Username and password are required.')
            return render_template('register.html')
        try:
            user = User.query.filter_by(username=username).first()
            if user is None:
                user = User(username=username)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                flash('Registration successful! You can now log in.')
                return redirect(url_for('login'))
            else:
                flash('Username already exists.')
        except Exception as e:
            print(f'Error during registration: {e}')
            db.session.rollback()
            flash('An error occurred during registration. Please try again.')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session['user_id'] = user.id
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password.')
        except Exception as e:
            print(f'Error during login: {e}')
            flash('An error occurred during login. Please try again.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/schedule', methods=['POST'])
def schedule_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    platform = request.form['platform']
    content = request.form['content']
    post_time = request.form['post_time']
    try:
        new_post = ScheduledPost(platform=platform, content=content, post_time=post_time, user_id=session['user_id'])
        db.session.add(new_post)
        db.session.commit()
        
        scheduler.add_job(post_to_social_media, 'date', run_date=post_time, args=[new_post.id], 
                          id=str(new_post.id), replace_existing=True, misfire_grace_time=3600)
        return redirect(url_for('index'))
    except Exception as e:
        print(f'Error scheduling post: {e}')
        db.session.rollback()
        flash('An error occurred while scheduling the post. Please try again.')
        return redirect(url_for('index'))

def post_to_social_media(post_id):
    post = ScheduledPost.query.get(post_id)
    try:
        response = requests.post(f'https://api.{post.platform}.com/post', data={'content': post.content})
        if response.status_code == 200:
            print(f'Post {post_id} successfully published to {post.platform}')
        else:
            print(f'Failed to publish post {post_id} to {post.platform}: {response.text}')
    except requests.RequestException as e:
        print(f'Error posting to {post.platform}: {e}')

def job_listener(event):
    if event.exception:
        print(f'Job {event.job_id} failed: {event.exception}')
    else:
        print(f'Job {event.job_id} succeeded')

scheduler.add_listener(job_listener, apscheduler.events.EVENT_JOB_EXECUTED | apscheduler.events.EVENT_JOB_ERROR)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
