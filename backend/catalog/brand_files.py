from django.db import transaction


def schedule_brand_logo_delete(name: str, storage, *, using: str) -> None:
    """Delete a replaced logo only after commit and only when unreferenced."""
    if not name:
        return

    def delete_if_unreferenced():
        from .models import Brand

        if not Brand.objects.using(using).filter(logo=name).exists():
            storage.delete(name)

    transaction.on_commit(delete_if_unreferenced, using=using, robust=True)
