import uuid

from aiogram.utils.formatting import as_marked_section

categories = ['Товар 1', '2', 'Товар 3', 'Товар 4']


def generate_unique_key():
    return str(uuid.uuid4())


unique_key = generate_unique_key()

description_for_info_pages = {
    "main": "Добро пожаловать!",
    "about": "Магазин\nРежим работы - круглосуточно.",
    "payment": as_marked_section(
        "Оплата заказа",
        f"Реквизиты для оплаты: ХХХХХХХХХХХХХ\n\n‼️ОБРАТИТЕ ВНИМАНИЕ‼️\nВаш уникальный ключ который ОБЯЗАТЕЛЬНО будет указать в коментарии при оплате чтоб мы смогли идентифицировать вас: {unique_key}\n\nПосле оплаты введите команду /confirm_payment",
        marker="✅",
    ).as_html(),
    'catalog': 'Категории:',
    'cart': 'В корзине ничего нет!'  # я текст как меняю он не менятеся в боте тк нужна база новая
}
