from telegram import Update
from telegram.ext import ContextTypes

from src.bot_service.clients.scrapper_client import scrapper_client
from ai_agent_service.logger import logger
from src.bot_service.tools import get_user_data, get_update_fields


async def list_links(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /list."""
    user, message, _ = get_update_fields(update)
    user_id = user.id

    tag = context.args[0] if context.args else None

    logger.info("list_links_command", user_id=user_id, tag=tag)

    links = await scrapper_client.get_links(user_id, tag)

    if not links:
        if tag:
            await message.reply_text(
                f"У вас нет отслеживаемых ссылок с тегом '{tag}'.\n\n"
                f"Используйте /track чтобы добавить ссылку."
            )
        else:
            await message.reply_text(
                "У вас пока нет отслеживаемых ссылок.\n\n"
                "Используйте /track, чтобы добавить первую ссылку."
            )
        return

    links_by_tag: dict = {}
    for link in links:
        if not link["tags"]:
            key = "Без тега"
        else:
            for tag in link["tags"]:
                key = tag
                if key not in links_by_tag:
                    links_by_tag[key] = []
                links_by_tag[key].append(link["url"])

        if not link["tags"]:
            if "Без тега" not in links_by_tag:
                links_by_tag["Без тега"] = []
            links_by_tag["Без тега"].append(link["url"])

    message_parts = ["📋 **Ваши отслеживаемые ссылки:**\n"]

    for tag_name, urls in sorted(links_by_tag.items()):
        message_parts.append(f"\n**{tag_name}:**")
        for i, url in enumerate(urls, 1):
            message_parts.append(f"{i}. {url}")

    if tag:
        message_parts.append(f"\n(отфильтровано по тегу: {tag})")

    message_parts.append(f"\nВсего: {len(links)} ссылок")

    await message.reply_text("\n".join(message_parts), parse_mode="Markdown")

    logger.info("links_listed", user_id=user_id, count=len(links), tag=tag)


async def untrack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /untrack."""
    user, update_message, _ = get_update_fields(update)
    user_id = user.id
    user_data = get_user_data(context)

    if not context.args:
        links = await scrapper_client.get_links(user_id)

        if not links:
            await update_message.reply_text("📭 У вас нет отслеживаемых ссылок.")
            return

        user_data["untrack_links"] = links

        message = ["**Выберите ссылку для удаления:**\n"]
        for i, link in enumerate(links, 1):
            tags_text = f" [теги: {', '.join(link['tags'])}]" if link["tags"] else ""
            message.append(f"{i}. {link['url']}{tags_text}")

        message.append("\nОтправьте **номер** ссылки для удаления.")
        message.append("Или отправьте /cancel для отмены.")

        await update_message.reply_text("\n".join(message), parse_mode="Markdown")
        return

    try:
        index = int(context.args[0]) - 1
        links = user_data.get("untrack_links", [])

        if 0 <= index < len(links):
            url = links[index]["url"]
        else:
            await update_message.reply_text("❌ Неверный номер. Попробуйте еще раз.")
            return

    except ValueError:
        url = context.args[0]

    success = await scrapper_client.remove_link(user_id, url)

    if success:
        await update_message.reply_text(f"✅ Отслеживание ссылки {url} прекращено.")
        logger.info("link_untracked", user_id=user_id, url=url)
    else:
        await update_message.reply_text(
            "❌ Ссылка не найдена. Возможно, она уже была удалена."
        )

    user_data.pop("untrack_links", None)


async def handle_untrack_choice(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user_data = get_user_data(context)
    user, message, _ = get_update_fields(update)
    """Обработчик выбора номера для /untrack."""
    if "untrack_links" not in user_data:
        return

    try:
        if message.text is not None:
            index = int(message.text) - 1
        else:
            index = 0
        links = user_data["untrack_links"]

        if 0 <= index < len(links):
            url = links[index]["url"]
            user_id = user.id

            success = await scrapper_client.remove_link(user_id, url)

            if success:
                await message.reply_text(f"✅ Отслеживание ссылки {url} прекращено.")
                logger.info("link_untracked", user_id=user_id, url=url)
            else:
                await message.reply_text("❌ Не удалось удалить ссылку.")
        else:
            await message.reply_text("❌ Неверный номер. Попробуйте еще раз.")

    except ValueError:
        await message.reply_text("❌ Пожалуйста, отправьте номер.")

    user_data.pop("untrack_links", None)
