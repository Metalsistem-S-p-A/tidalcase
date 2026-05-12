import celery
import docker
import routes.config
import utils


@celery.shared_task
def prune_images() -> None:
    config = routes.config.agent_config
    mode = config.get('prune_mode', 'off')
    if mode == 'off':
        return
    app_image_set = set(config.get('app_image_set', []))

    try:
        result = docker.from_env().images.prune(filters={"dangling": True})
        freed = result.get('SpaceReclaimed', 0)
        print(f"[agent] Prune dangling: freed {utils.fmt_bytes(freed)}", flush=True)
    except Exception as e:
        print(f"[agent] Prune error: {e}", flush=True)
        return

    if mode == 'aggressive' and app_image_set:
        for img in docker.from_env().images.list():
            tags = img.tags
            if not tags:
                continue
            if not any(t in app_image_set for t in tags):
                try:
                    docker.from_env().images.remove(img.id, force=False, noprune=False)
                    print(f"[agent] Pruned non-app image {tags[0]}", flush=True)
                except Exception:
                    pass
