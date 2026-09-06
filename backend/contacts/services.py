from django.db import transaction
from django.db.models import Max

from footer.revalidation import schedule_footer_revalidation
from .models import FloatingContactButton


def schedule_icon_delete(name, storage, *, using):
    if name:
        def delete_unreferenced():
            if not FloatingContactButton.objects.using(using).filter(icon=name).exists():
                storage.delete(name)
        transaction.on_commit(delete_unreferenced, using=using, robust=True)


@transaction.atomic
def create_button(**fields):
    if "display_order" not in fields:
        last = FloatingContactButton.objects.aggregate(value=Max("display_order"))["value"]
        fields["display_order"] = 0 if last is None else last + 1
    button = FloatingContactButton(**fields)
    button.save()
    # Shared tag also invalidates these buttons when a library icon is replaced.
    schedule_footer_revalidation(using=button._state.db)
    return button


@transaction.atomic
def update_button(button, **fields):
    button = FloatingContactButton.objects.select_for_update().get(pk=button.pk)
    old_name, storage = button.icon.name, button.icon.storage
    for field, value in fields.items():
        setattr(button, field, value)
    button.save()
    if old_name != button.icon.name:
        schedule_icon_delete(old_name, storage, using=button._state.db)
    schedule_footer_revalidation(using=button._state.db)
    return button


@transaction.atomic
def delete_button(button):
    button = FloatingContactButton.objects.select_for_update().get(pk=button.pk)
    name, storage, using = button.icon.name, button.icon.storage, button._state.db
    button.delete()
    schedule_icon_delete(name, storage, using=using)
    schedule_footer_revalidation(using=using)


@transaction.atomic
def move_button(button, direction):
    rows = list(FloatingContactButton.objects.select_for_update().order_by("display_order", "id"))
    # Order is independent on each physical side, matching the two visible stacks.
    indices = [i for i, row in enumerate(rows) if row.position == button.position]
    index = next(i for i, row_index in enumerate(indices) if rows[row_index].pk == button.pk)
    neighbor = index + (-1 if direction == "up" else 1)
    if 0 <= neighbor < len(indices):
        a, b = indices[index], indices[neighbor]
        rows[a], rows[b] = rows[b], rows[a]
        for order, row in enumerate(rows):
            row.display_order = order
        FloatingContactButton.objects.bulk_update(rows, ["display_order"])
        schedule_footer_revalidation(using=button._state.db)
