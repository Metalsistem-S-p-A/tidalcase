import app
import app.utils.celery_app

tidalcase_app = app.create_app()
celery_app = app.utils.celery_app.make_celery(tidalcase_app)
