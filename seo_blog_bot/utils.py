import structlog


def get_seo_blog_bot_logger(name):
    """This will add a `seo_blog_bot` prefix to logger for easy configuration."""

    return structlog.get_logger(
        f"seo_blog_bot.{name}",
        project="seo_blog_bot",
    )
