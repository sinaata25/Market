from django.db import transaction
from django.db.models import Q


def schedule_banner_image_delete(name: str, storage, *, using: str) -> None:
    """Delete an unreferenced banner image only after the database change commits."""
    if not name:
        return

    def delete_if_unreferenced():
        from .models import BANNER_IMAGE_FIELDS, Banner

        # هر دو نسخه‌ی تصویر بررسی می‌شوند تا فایلی که هنوز جای دیگری
        # استفاده می‌شود (مثلاً همان فایل به‌عنوان تصویر موبایل) حذف نشود
        referenced = Q()
        for field_name in BANNER_IMAGE_FIELDS.values():
            referenced |= Q(**{field_name: name})
        if not Banner.objects.using(using).filter(referenced).exists():
            storage.delete(name)

    transaction.on_commit(delete_if_unreferenced, using=using, robust=True)
