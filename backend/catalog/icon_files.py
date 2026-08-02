from django.db import transaction


def schedule_category_icon_delete(name: str, storage, *, using: str) -> None:
    """Delete an unreferenced icon only after the database change commits."""
    if not name:
        return

    def delete_if_unreferenced():
        from .models import Category

        if not Category.objects.using(using).filter(icon=name).exists():
            storage.delete(name)

    transaction.on_commit(delete_if_unreferenced, using=using, robust=True)
