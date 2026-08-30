from django.db import transaction


def schedule_footer_image_delete(name: str, storage, *, using: str) -> None:
    """Delete a replaced footer image only after commit and only when unreferenced."""
    if not name:
        return

    def delete_if_unreferenced():
        from .models import FooterItem, FooterSettings

        referenced = (
            FooterSettings.objects.using(using).filter(logo=name).exists()
            or FooterItem.objects.using(using).filter(image=name).exists()
        )
        if not referenced:
            storage.delete(name)

    transaction.on_commit(delete_if_unreferenced, using=using, robust=True)
