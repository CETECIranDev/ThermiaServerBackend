import os
from celery import Celery

# Set default Django settings module so Celery knows where Django config is
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TermiaWebBackend.settings')

# Create Celery application instance
app = Celery('TermiaWebBackend')

# Load Celery configuration from Django settings.py
# Only settings prefixed with "CELERY_" will be applied
app.config_from_object('django.conf:settings', namespace='CELERY')

# Automatically discover tasks.py files in all registered Django apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    # Simple debug task to inspect Celery request context
    print(f'Request: {self.request!r}')