from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import requests
from app import db, ScheduledPost  # Import the db and models from app.py

scheduler = BackgroundScheduler()
scheduler.start()

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

# Register the job listener
scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
