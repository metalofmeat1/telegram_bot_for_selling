import os
import json
import asyncio
import uuid

from aiogram import F, types, Router, Bot
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command

from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_add_to_cart, orm_add_user, orm_get_user_carts
from database.models import User

from filters.chat_types import ChatTypeFilter

from handlers.menu_processing import get_menu_content, products

from kbds.inline import MenuCallBack, get_callback_btns

bot = Bot(token=os.getenv('TOKEN'))

# Initialize the bot
# bot = Bot(token=os.getenv('TOKEN'))
user_private_router = Router()
user_private_router.message.filter(ChatTypeFilter(["private"]))

admins_file = 'admins.json'
couriers_file = 'couriers.json'


def generate_unique_key():
    return str(uuid.uuid4())


# Helper functions for JSON file operations
def read_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return []


def write_json(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f)


def add_id(file_path, new_id):
    ids = read_json(file_path)
    if new_id not in ids:
        ids.append(new_id)
        write_json(file_path, ids)


def remove_id(file_path, remove_id):
    ids = read_json(file_path)
    if remove_id in ids:
        ids.remove(remove_id)
        write_json(file_path, ids)


# Ensure admin ID is set
async def ensure_admin_set():
    admins = read_json(admins_file)
    if not admins:
        add_id(admins_file, '6588562022')


# Initialize admin data
asyncio.run(ensure_admin_set())


# Handlers
@user_private_router.message(CommandStart())
async def start_cmd(message: types.Message, session: AsyncSession):
    media, reply_markup = await get_menu_content(session, level=0, menu_name="main")
    await message.answer_photo(media.media, caption=media.caption, reply_markup=reply_markup)


@user_private_router.message(Command('confirm_payment'))
async def confirm_payment(message: types.Message, session: AsyncSession):
    user_id = message.from_user.id
    try:
        user = await session.get(User, user_id)

        if user:
            # Fetching the user's cart and calculating the total price
            carts = orm_get_user_carts()

            # Generating a unique key for the current order
            unique_key = generate_unique_key()

            # Reading admin and delivery IDs from JSON files
            admin_ids = read_json(admins_file)
            delivery_ids = read_json(couriers_file)

            if not admin_ids and not delivery_ids:
                await message.reply("⚠️ Нет доступных ID для уведомления.")
                return

            # Message to be sent
            order_message = (
                f"Новый заказ от пользователя {message.from_user.full_name} (@{message.from_user.username}):\n\n"
                f"‼️ ОБРАТИТЕ ВНИМАНИЕ ‼️\n"
                f"Ваш уникальный ключ который ОБЯЗАТЕЛЬНО нужно указать в комментарии при оплате, чтобы мы могли вас идентифицировать: {unique_key}\n\n"
            )

            # Sending message to admins
            for admin_id in admin_ids:
                try:
                    await bot.send_message(admin_id, order_message, parse_mode=ParseMode.HTML)
                except Exception as e:
                    print(f"Не удалось отправить сообщение администратору {admin_id}: {e}")

            # Sending message to delivery IDs
            for delivery_id in delivery_ids:
                try:
                    await bot.send_message(f'Новый заказ от пользователя {message.from_user.full_name} (@{message.from_user.username}):\n\n', delivery_id, parse_mode=ParseMode.HTML)
                except Exception as e:
                    print(f"Не удалось отправить сообщение доставщику {delivery_id}: {e}")

            # Sending the user's cart details to admins and couriers
            for admin_id in admin_ids:
                try:
                    media, reply_markup = await get_menu_content(
                        session,
                        level=2,
                        menu_name="cart",
                        user_id=user_id
                    )
                    await bot.send_media_group(admin_id, [media])
                except Exception as e:
                    print(f"Не удалось отправить сообщение с корзиной администратору {admin_id}: {e}")

            for delivery_id in delivery_ids:
                try:
                    media, reply_markup = await get_menu_content(
                        session,
                        level=2,
                        menu_name="cart",
                        user_id=user_id
                    )
                    await bot.send_media_group(delivery_id, [media])
                except Exception as e:
                    print(f"Не удалось отправить сообщение с корзиной доставщику {delivery_id}: {e}")

            await message.reply("Оплата подтверждена. Ожидайте сообщение от менеджера.")
        else:
            await message.reply("Ваши данные не найдены. Попробуйте добавить товары в корзину заново.")
    except Exception as e:
        print(f"Ошибка при обработке команды /confirm_payment: {e}")
        await message.reply("Оплата подтверждена. Ожидайте сообщение от менеджера.")


@user_private_router.message(Command('add_delivery_id'))
async def handle_add_delivery_id(message: types.Message):
    admin_ids = read_json(admins_file)
    if str(message.from_user.id) not in admin_ids:
        await message.reply("⚠️ Вы не являетесь администратором.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        await message.reply("⚙️ Неверный формат команды. Используйте /add_delivery_id [ID].")
        return

    new_id = args[1]
    if new_id in read_json(couriers_file):
        await message.reply("⚠️ Этот ID уже существует в списке.")
        return

    add_id(couriers_file, new_id)
    await message.reply(f"ID {new_id} добавлен в список доставки.")


@user_private_router.message(Command('remove_delivery_id'))
async def handle_remove_delivery_id(message: types.Message):
    admin_ids = read_json(admins_file)
    if str(message.from_user.id) not in admin_ids:
        await message.reply("⚠️ Вы не являетесь администратором.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        await message.reply("⚙️ Неверный формат команды. Используйте /remove_delivery_id [ID].")
        return

    remove_id_not_func = args[1]
    if remove_id_not_func not in read_json(couriers_file):
        await message.reply("⚠️ Этот ID не найден в списке.")
        return

    remove_id(couriers_file, remove_id_not_func)
    await message.reply(f"ID {remove_id_not_func} удален из списка доставки.")


@user_private_router.message(Command('msg'))
async def reject_request(message: types.Message):
    admin_ids = read_json(admins_file)
    if str(message.from_user.id) not in admin_ids:
        return

    user_id, category = parse_command_args(message.text)
    if user_id is None or category is None:
        await message.answer("⚙️ Неверный формат команды. Используйте /msg [user_id] [сообщение покупателю].")
        return

    await bot.send_message(user_id, f"️Сообщение от админа: '{category}'")
    await message.answer(f"Смс отправлен пользователю {user_id}")


# Helper function to parse command arguments
def parse_command_args(command_text):
    parts = command_text.split(maxsplit=2)
    if len(parts) != 3:
        return None, None
    try:
        user_id = int(parts[1])
    except ValueError:
        return None, None
    return user_id, parts[2]


# Function to add item to cart
async def add_to_cart(callback: types.CallbackQuery, callback_data: MenuCallBack, session: AsyncSession):
    user = callback.from_user
    await orm_add_user(session, user_id=user.id, first_name=user.first_name, last_name=user.last_name, phone=None)
    await orm_add_to_cart(session, user_id=user.id, product_id=callback_data.product_id)
    await callback.answer("Товар добавлен в корзину.")


# Handler for menu callbacks
@user_private_router.callback_query(MenuCallBack.filter())
async def user_menu(callback: types.CallbackQuery, callback_data: MenuCallBack, session: AsyncSession):
    if callback_data.menu_name == "add_to_cart":
        await add_to_cart(callback, callback_data, session)
        return

    media, reply_markup = await get_menu_content(
        session,
        level=callback_data.level,
        menu_name=callback_data.menu_name,
        category=callback_data.category,
        page=callback_data.page,
        product_id=callback_data.product_id,
        user_id=callback.from_user.id,
    )

    await callback.message.edit_media(media=media, reply_markup=reply_markup)
    await callback.answer()

########################


from aiogram.types import InputMediaPhoto
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_add_to_cart,
    orm_delete_from_cart,
    orm_get_banner,
    orm_get_categories,
    orm_get_products,
    orm_get_user_carts,
    orm_reduce_product_in_cart,
)
from kbds.inline import (
    get_products_btns,
    get_user_cart,
    get_user_catalog_btns,
    get_user_main_btns,
)

from utils.paginator import Paginator


async def main_menu(session, level, menu_name):
    banner = await orm_get_banner(session, menu_name)
    image = InputMediaPhoto(media=banner.image, caption=banner.description)

    kbds = get_user_main_btns(level=level)

    return image, kbds


async def catalog(session, level, menu_name):
    banner = await orm_get_banner(session, menu_name)
    image = InputMediaPhoto(media=banner.image, caption=banner.description)

    categories = await orm_get_categories(session)
    kbds = get_user_catalog_btns(level=level, categories=categories)

    return image, kbds


def pages(paginator: Paginator):
    btns = dict()
    if paginator.has_previous():
        btns["◀ Пред."] = "previous"

    if paginator.has_next():
        btns["След. ▶"] = "next"

    return btns


async def products(session, level, category, page):
    products = await orm_get_products(session, category_id=category)

    paginator = Paginator(products, page=page)
    product = paginator.get_page()[0]

    caption2 = (
        f"{product.name}\n\n"
        f"Описание: {product.description}\n\n"
        f"Стоимость: {round(product.price, 2)}$\n"
        f"Товар {paginator.page} из {paginator.pages}"
    )

    image = InputMediaPhoto(
        media=product.image,
        caption=caption2
    )

    pagination_btns = pages(paginator)

    kbds = get_products_btns(
        level=level,
        category=category,
        page=page,
        pagination_btns=pagination_btns,
        product_id=product.id,
    )

    return image, kbds


async def carts(session, level, menu_name, page, user_id, product_id):
    if menu_name == "delete":
        await orm_delete_from_cart(session, user_id, product_id)
        if page > 1:
            page -= 1
    elif menu_name == "decrement":
        is_cart = await orm_reduce_product_in_cart(session, user_id, product_id)
        if page > 1 and not is_cart:
            page -= 1
    elif menu_name == "increment":
        await orm_add_to_cart(session, user_id, product_id)

    carts = await orm_get_user_carts(session, user_id)

    if not carts:
        banner = await orm_get_banner(session, "cart")
        image = InputMediaPhoto(
            media=banner.image, caption=f"{banner.description}"
        )

        kbds = get_user_cart(
            level=level,
            page=None,
            pagination_btns=None,
            product_id=None,
        )

    else:
        paginator = Paginator(carts, page=page)

        cart = paginator.get_page()[0]

        cart_price = round(cart.quantity * cart.product.price, 2)
        total_price = round(
            sum(cart.quantity * cart.product.price for cart in carts), 2
        )
        image = InputMediaPhoto(
            media=cart.product.image,
            caption=f"{cart.product.name}\n{cart.product.price}$ x {cart.quantity} = {cart_price}$\
                    \nТовар {paginator.page} из {paginator.pages} в корзине.\nОбщая стоимость товаров в корзине {total_price}",
        )

        pagination_btns = pages(paginator)

        kbds = get_user_cart(
            level=level,
            page=page,
            pagination_btns=pagination_btns,
            product_id=cart.product.id,
        )

    return image, kbds


async def get_menu_content(
        session: AsyncSession,
        level: int,
        menu_name: str,
        category: int | None = None,
        page: int | None = None,
        product_id: int | None = None,
        user_id: int | None = None,
):
    if level == 0:
        return await main_menu(session, level, menu_name)
    elif level == 1:
        return await catalog(session, level, menu_name)
    elif level == 2:
        return await products(session, level, category, page)
    elif level == 3:
        return await carts(session, level, menu_name, page, user_id, product_id)
