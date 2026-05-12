import os
import celery

def make_celery(app):
    class FlaskTask(celery.Task):
        def run(self, *args, **kwargs):
            pass

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_instance = celery.Celery(app.import_name)
    celery_instance.conf.update(
        broker_url=os.environ.get('CELERY_BROKER_URL', 'redis://tidalcase-redis:6379/0'),
        result_backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://tidalcase-redis:6379/0'),
        task_ignore_result=True,
        imports=[
            'app.celery_tasks.agent_monitor',
        ]
    )

    celery_instance.conf.beat_schedule = {
        'run-monitor-every-5-minutes': {
            'task': 'app.celery_tasks.agent_monitor.agent_monitor_task',
            'schedule': 300.0,
        },
    }

    celery_instance.Task = FlaskTask
    return celery_instance
