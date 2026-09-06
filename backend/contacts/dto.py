from footer.dto import icon_url


def button_dto(button):
    return {
        "id": button.pk,
        "title": button.title,
        "platform": button.platform,
        "url": button.destination,
        "icon": button.icon.url if button.icon else icon_url(button.library_icon),
        "iconName": button.icon_name or button.platform,
        "tooltipText": button.tooltip_text,
        "openInNewTab": button.open_in_new_tab,
        "position": button.position,
        "displayOrder": button.display_order,
    }


def admin_button_dto(button):
    return {
        **button_dto(button),
        "rawUrl": button.url,
        "phoneNumber": button.phone_number,
        "username": button.username,
        "email": button.email,
        "iconName": button.icon_name,
        "iconId": button.library_icon_id,
        "uploadedIcon": button.icon.url if button.icon else None,
        "isActive": button.is_active,
    }
