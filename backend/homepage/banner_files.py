from django.db import transaction


def schedule_banner_image_delete(name: str, storage, *, using: str) -> None:
    """Delete an unreferenced banner image only after the database change commits."""
    if not name:
        return

    def delete_if_unreferenced():
        from .models import Banner

        if not Banner.objects.using(using).filter(image=name).exists():
            storage.delete(name)

    transaction.on_commit(delete_if_unreferenced, using=using, robust=True)
