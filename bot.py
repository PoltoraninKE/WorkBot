# Импорты стандартных библиотек
import requests
import asyncio
import logging
import sys
import aiohttp
from aiohttp import ClientResponse

# Импорты библиотеки для работы с телегой
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

# Запоминаем токены пока так - нужно будет сделать секурно - сделаем секурно 8)
BOT_TOKEN = 'YOUR_BOT_TOKEN_FROM_BOT_FATHER'
YA_OAUTH_TOKEN = 'YOUR_YANDEX_DISK_TOKEN'

# Яндекс по API отдает 201 вместо 200, если всё ок. Бог им судья.
YANDEX_FOLDER_CREATED_SUCCESSFULL_CODE = 201

# Если такая папка уже существует, тогда яндекс вернет нам 409
YANDEX_FOLDER_EXISTS_CODE = 409

# У них ещё есть преколы. Пошли они на 404
YANDEX_FILE_CREATED_CODE = 202

# Объявляю тут, потому что нужно дальше
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# Урл, с помощью которого будем качать файлики с сервера телеграма
TELEGRAM_URL = f"https://api.telegram.org/file/bot{BOT_TOKEN}/"

# Для диспатча (ответов на какие-то взаимодействия с ботом) сообщений
dp = Dispatcher()

# Обработчик команды /start
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer("Добро пожаловать Введите адрес для создания отчета.")


# Обработчик любого текста. Если написать текст боту - он создаст такую папку. 
@dp.message()
async def make_disk_directory(message: Message) -> None:

    # Если это не текст, тогда, возможно, это фото.
    if message.text is None:
        await download_photo(message)
        logging.log(level=logging.INFO, msg="message.text is None")
        return

    # Собираем Header'ы для запросов в Api яндекс.диска.
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'OAuth {YA_OAUTH_TOKEN}'    
    }

    # Тут создаем http-клиент, для общения с api яндекса и отправляем нужный нам PUT запрос.
    async with aiohttp.ClientSession() as session:
        async with session.put(f"https://cloud-api.yandex.net/v1/disk/resources?path={message.text}", headers=headers) as response:
            # Если папка создалась, нам вернут SUCCESSFULL_CODE. 
            if response.status == YANDEX_FOLDER_CREATED_SUCCESSFULL_CODE:
                await message.answer('Адрес создан')
                global CURRENT_FOLDER
                CURRENT_FOLDER = message.text
            # Если не success, значит проверим, что папка уже есть. Если есть, то запомним, что выбор пал на нее.
            elif response.status == YANDEX_FOLDER_EXISTS_CODE:
                await message.answer(f'Папка {message.text} выбрана')
                CURRENT_FOLDER = message.text
            # Всё остальное коды ошибок - придут в сообщении пользователю, а также залогируется в консольку.
            else:
                logging.error(response.text)
                await message.answer(f'Ошибка: {response.text}')


# Обработчик фотографий
@dp.message()
async def download_photo(message: Message) -> None:

    # Берем последнее отправленное фото
    photo = message.photo[-1]

    # Если это не фотография, тогда напишем об этом в лог и дальше не будем ничего делать
    if photo is None:
        logging.log(level=logging.INFO, msg="photo is None")
        return
        
    # Собираем информацию по поводу фотографии, что нам отправили
    file_id = photo.file_id
    file_info = await bot.get_file(file_id)

    # Путь, где на серваке телеги лежит эта фотка
    file_path = file_info.file_path

    # Собираем инфу по поводу пути до файла, откуда качать на диск
    url_to_download_file_from_telegram = TELEGRAM_URL + file_path
    file_name = file_path.replace('photos/', '')
    # Собираем инфу по поводу того, куда на диске сохраняем этот файл
    file_path_to_save_on_ya_disk = CURRENT_FOLDER + '/' + file_name
    response = await upload_file_to_yandex_disk(url_to_download_file_from_telegram, file_path_to_save_on_ya_disk)

    # Если файлик создался - пишем, что всё ок, файлик можно тыкать.
    if response.status == YANDEX_FILE_CREATED_CODE:
        await message.answer('Фотография загружена. Давай следующую')
    # Иначе логируем ошибку и пишем о ней пользователю.
    else:
        logging.error(response.text())
        await message.answer(f'Ошибка. {response.json()}. Обратись к разработчику, что у него тут сломано.')

# Функция сохранения файлика на диск
async def upload_file_to_yandex_disk(file_url: str, path: str) -> ClientResponse:

    # Вновь собираем headers, для запроса в YaD
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'OAuth {YA_OAUTH_TOKEN}'
    }

    # Тут создаем http-клиент, для общения с api яндекса, чтобы отправить
    async with aiohttp.ClientSession() as session:
        async with session.post(f'https://cloud-api.yandex.net/v1/disk/resources/upload?path={path}&url={file_url}', headers=headers) as response:
            return response

async def main() -> None:    
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

