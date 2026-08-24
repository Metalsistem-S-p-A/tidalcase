"""Periodic cleanup of orphan tide containers on registered agents.

A container is "orphan" when it is running on an agent but its UUID does not
match any row in `tide_instance`. The manager cannot enforce its session or
idle timeout on it (it does not know it exists), so without this task the
container would live until the agent's own container timeout — or forever.
"""
import celery
import app.models.agent
import app.models.tide
import app.utils.docker
import app.utils.logger


@celery.shared_task
def cleanup_orphan_instances_task():
    agents = app.models.agent.Agent.query.filter_by(enabled=True).all()
    for agent in agents:
        if not agent.api_url or not agent.api_token:
            continue
        client = app.utils.docker.get_agent_client(agent)
        if client is None:
            continue

        try:
            data = client.get_container_stats()
        except Exception as e:
            app.utils.logger.log(
                "WARN",
                f"[orphan-cleanup] {agent.display_name}: stats fetch failed: {e}",
            )
            continue

        raw_instances = data.get('instances', []) or []
        if not raw_instances:
            continue

        instance_ids = [i['instance_id'] for i in raw_instances]
        existing_ids = {
            str(row.id)
            for row in app.models.tide.TideInstance.query
                .with_entities(app.models.tide.TideInstance.id)
                .filter(app.models.tide.TideInstance.id.in_(instance_ids))
                .all()
        }

        for raw in raw_instances:
            if raw['instance_id'] in existing_ids:
                continue
            name = raw.get('container_name') or f"tidalcase-{raw['instance_id']}"
            try:
                client.remove_container(name)
                app.utils.logger.log(
                    "INFO",
                    f"[orphan-cleanup] {agent.display_name}: removed orphan {name}",
                )
            except Exception as e:
                app.utils.logger.log(
                    "WARN",
                    f"[orphan-cleanup] {agent.display_name}: remove {name} failed: {e}",
                )
