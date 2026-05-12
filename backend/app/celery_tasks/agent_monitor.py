import datetime
import celery
import app.models.agent
import app.utils.extensions

@celery.shared_task
def agent_monitor_task():
    agents = app.models.agent.Agent.query.filter_by(enabled=True).all()
    now = datetime.datetime.now()
    for agent in agents:
        if agent.last_healthcheck_at:
            agent.healthy = (now - agent.last_healthcheck_at) < datetime.timedelta(seconds=90)
        else:
            agent.healthy = False
    app.utils.extensions.db.session.commit()
