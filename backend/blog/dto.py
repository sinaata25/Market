from .models import BlogCategory, BlogPost, BlogTag


def category_dto(category: BlogCategory) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
    }


def tag_dto(tag: BlogTag) -> dict:
    return {"id": tag.id, "name": tag.name, "slug": tag.slug}


def post_dto(
    post: BlogPost, *, include_content: bool = False, include_admin: bool = False
) -> dict:
    data = {
        "id": post.id,
        "title": post.title,
        "slug": post.slug,
        "excerpt": post.excerpt,
        "featuredImage": post.featured_image.url if post.featured_image else None,
        "author": {
            "id": post.author_id,
            "name": post.author.name or "مدیریت فروشگاه",
        },
        "category": category_dto(post.category) if post.category else None,
        "tags": [tag_dto(tag) for tag in post.tags.all()],
        "status": post.status,
        "publishedAt": post.published_at.isoformat() if post.published_at else None,
        "seoTitle": post.seo_title,
        "seoDescription": post.seo_description,
    }
    if include_content:
        data["content"] = post.content
    if include_admin:
        data.update(
            {
                "createdAt": post.created_at.isoformat(),
                "updatedAt": post.updated_at.isoformat(),
            }
        )
    return data
