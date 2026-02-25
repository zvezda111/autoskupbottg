import os
import random
import zipfile
import logging
import csv
import tempfile
import shutil
import asyncio
import pycountry
import json
import string
import uuid
from typing import Dict
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import socks
import telethon
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import aiofiles
import phonenumbers
from phonenumbers import geocoder
from sqlalchemy import update
from dotenv import load_dotenv
from aiogram import types
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, \
    Message
from app.bot.src.crtdb import *
from app.bot.session_cloner import *

from app.bot.session_cloner import clone_session
from telethon import TelegramClient, events
from telethon.errors import PeerFloodError, rpcerrorlist
from sqlalchemy import select, func
from app.db.database import engine, AsyncSessionLocal, Base
from app.db.models import Check, Price, WithdrawStatus, User, UserPrice, MinWithdrawal, MaxAccs
from app.services.db_services import (
    get_or_create_user,
    get_or_create_session,
    create_check,
    get_stats,
    request_withdrawal,
    list_pending_withdrawals,
    change_withdrawal_status
)
from app.services.price_services import (
    get_effective_prices,
    set_default_price,
    set_user_price,
    delete_region
)

#————————————————————————
#Настройка
load_dotenv()
API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
raw = os.getenv("ADMIN_ID", "")
ADMIN_ID = [int(x.strip()) for x in raw.split(",") if x.strip()]
TEMP_DIR = os.path.join(os.getcwd(), 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)
SESSIONS_EXPORT_DIR = os.path.join(os.getcwd(), 'exported_sessions')
VALID_DIR = os.path.join(SESSIONS_EXPORT_DIR, 'valid')
SPAM_DIR = os.path.join(SESSIONS_EXPORT_DIR, 'spam')
country_names_ru = {
    "AD": "Андорра",
    "AE": "Объединённые Арабские Эмираты",
    "AF": "Афганистан",
    "AG": "Антигуа и Барбуда",
    "AI": "Ангилья",
    "AL": "Албания",
    "AM": "Армения",
    "AO": "Ангола",
    "AR": "Аргентина",
    "AT": "Австрия",
    "AU": "Австралия",
    "AZ": "Азербайджан",
    "BA": "Босния и Герцеговина",
    "BB": "Барбадос",
    "BD": "Бангладеш",
    "BE": "Бельгия",
    "BF": "Буркина-Фасо",
    "BG": "Болгария",
    "BH": "Бахрейн",
    "BI": "Бурунди",
    "BJ": "Бенин",
    "BN": "Бруней",
    "BO": "Боливия",
    "BR": "Бразилия",
    "BS": "Багамские Острова",
    "BT": "Бутан",
    "BW": "Ботсвана",
    "BY": "Беларусь",
    "BZ": "Белиз",
    "CA": "Канада",
    "CD": "Демократическая Республика Конго",
    "CF": "Центральноафриканская Республика",
    "CG": "Республика Конго",
    "CH": "Швейцария",
    "CI": "Кот-д’Ивуар",
    "CL": "Чили",
    "CM": "Камерун",
    "CN": "Китай",
    "CO": "Колумбия",
    "CR": "Коста-Рика",
    "CU": "Куба",
    "CV": "Кабо-Верде",
    "CY": "Кипр",
    "CZ": "Чехия",
    "DE": "Германия",
    "DJ": "Джибути",
    "DK": "Дания",
    "DM": "Доминика",
    "DO": "Доминиканская Республика",
    "DZ": "Алжир",
    "EC": "Эквадор",
    "EE": "Эстония",
    "EG": "Египет",
    "ER": "Эритрея",
    "ES": "Испания",
    "ET": "Эфиопия",
    "FI": "Финляндия",
    "FJ": "Фиджи",
    "FM": "Микронезия",
    "FR": "Франция",
    "GA": "Габон",
    "GB": "Великобритания",
    "GD": "Гренада",
    "GE": "Грузия",
    "GH": "Гана",
    "GM": "Гамбия",
    "GN": "Гвинея",
    "GQ": "Экваториальная Гвинея",
    "GR": "Греция",
    "GT": "Гватемала",
    "GW": "Гвинея-Бисау",
    "GY": "Гайана",
    "HN": "Гондурас",
    "HR": "Хорватия",
    "HT": "Гаити",
    "HU": "Венгрия",
    "ID": "Индонезия",
    "IE": "Ирландия",
    "IL": "Израиль",
    "IN": "Индия",
    "IQ": "Ирак",
    "IR": "Иран",
    "IS": "Исландия",
    "IT": "Италия",
    "JM": "Ямайка",
    "JO": "Иордания",
    "JP": "Япония",
    "KE": "Кения",
    "KG": "Киргизия",
    "KH": "Камбоджа",
    "KI": "Кирибати",
    "KM": "Коморы",
    "KN": "Сент-Китс и Невис",
    "KP": "Северная Корея",
    "KR": "Южная Корея",
    "KW": "Кувейт",
    "KZ": "Казахстан",
    "LA": "Лаос",
    "LB": "Ливан",
    "LC": "Сент-Люсия",
    "LI": "Лихтенштейн",
    "LK": "Шри-Ланка",
    "LR": "Либерия",
    "LS": "Лесото",
    "LT": "Литва",
    "LU": "Люксембург",
    "LV": "Латвия",
    "LY": "Ливия",
    "MA": "Марокко",
    "MC": "Монако",
    "MD": "Молдова",
    "ME": "Черногория",
    "MG": "Мадагаскар",
    "MH": "Маршалловы Острова",
    "MK": "Северная Македония",
    "ML": "Мали",
    "MM": "Мьянма",
    "MN": "Монголия",
    "MR": "Мавритания",
    "MT": "Мальта",
    "MU": "Маврикий",
    "MV": "Мальдивы",
    "MW": "Малави",
    "MX": "Мексика",
    "MY": "Малайзия",
    "MZ": "Мозамбик",
    "NA": "Намибия",
    "NE": "Нигер",
    "NG": "Нигерия",
    "NI": "Никарагуа",
    "NL": "Нидерланды",
    "NO": "Норвегия",
    "NP": "Непал",
    "NR": "Науру",
    "NZ": "Новая Зеландия",
    "OM": "Оман",
    "PA": "Панама",
    "PE": "Перу",
    "PG": "Папуа — Новая Гвинея",
    "PH": "Филиппины",
    "PK": "Пакистан",
    "PL": "Польша",
    "PT": "Португалия",
    "PW": "Палау",
    "PY": "Парагвай",
    "QA": "Катар",
    "RO": "Румыния",
    "RS": "Сербия",
    "RU": "Россия",
    "RW": "Руанда",
    "SA": "Саудовская Аравия",
    "SB": "Соломоновы Острова",
    "SC": "Сейшельские Острова",
    "SD": "Судан",
    "SE": "Швеция",
    "SG": "Сингапур",
    "SI": "Словения",
    "SK": "Словакия",
    "SL": "Сьерра-Леоне",
    "SM": "Сан-Марино",
    "SN": "Сенегал",
    "SO": "Сомали",
    "SR": "Суринам",
    "SS": "Южный Судан",
    "ST": "Сан-Томе и Принсипи",
    "SV": "Сальвадор",
    "SY": "Сирия",
    "SZ": "Эсватини",
    "TD": "Чад",
    "TG": "Того",
    "TH": "Таиланд",
    "TJ": "Таджикистан",
    "TL": "Восточный Тимор",
    "TM": "Туркменистан",
    "TN": "Тунис",
    "TO": "Тонга",
    "TR": "Турция",
    "TT": "Тринидад и Тобаго",
    "TV": "Тувалу",
    "TW": "Тайвань",
    "TZ": "Танзания",
    "UA": "Украина",
    "UG": "Уганда",
    "US": "США",
    "UY": "Уругвай",
    "UZ": "Узбекистан",
    "VA": "Ватикан",
    "VC": "Сент-Винсент и Гренадины",
    "VE": "Венесуэла",
    "VN": "Вьетнам",
    "VU": "Вануату",
    "WS": "Самоа",
    "YE": "Йемен",
    "ZA": "Южная Африка",
    "ZM": "Замбия",
    "ZW": "Зимбабве",
}
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger('sqlalchemy.engine.Engine').setLevel(logging.NOTSET)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
logs_dir = Path("logs_bot")
logs_dir.mkdir(exist_ok=True)
log_file = logs_dir / f"session_cloner_{datetime.now().strftime('%Y%m%d')}.log"
file_handler = logging.FileHandler(
    log_file,
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(
    logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')
)
logger.addHandler(file_handler)
os.makedirs(VALID_DIR, exist_ok=True)
os.makedirs(SPAM_DIR, exist_ok=True)

if not (API_ID and API_HASH and BOT_TOKEN):
    raise RuntimeError("Не заданы TELEGRAM_API_ID, TELEGRAM_API_HASH или BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()

profile_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👤 Профиль")], [KeyboardButton(text="💰 Цены")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)


#————————————————————————
#/start
def get_flag_emoji(iso_code):
    """Преобразует alpha_2 кодв эмодзи флага"""
    try:
        if len(iso_code) != 2 or not iso_code.isalpha():
            return iso_code
        base = ord('🇦')
        emoji = ''.join(chr(base + (ord(c.upper()) - ord('A'))) for c in iso_code[:2])
        return emoji
    except Exception:
        return iso_code


def generate_code(length=5):
    characters = string.ascii_letters + string.digits  # все буквы и цифры
    return ''.join(random.choice(characters) for _ in range(length))


def remove_user(user_id, filename, message):
    """Удаляет user_id из файла если он там есть"""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        user_found = False
        with open(filename, 'w', encoding='utf-8') as file:
            for line in lines:
                if line.strip() == str(user_id):
                    user_found = True
                    continue
                file.write(line)

        if user_found:
            return f"Пользователь {user_id} удален."
        else:
            return f"Пользователь {user_id} не найден."
    except FileNotFoundError:
        return "Файл не найден. Невозможно удалить пользователя."


def check_user_exists(user_id, filename):
    """Проверяет наличие user_id в файле"""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            for line in file:
                if line.strip() == str(user_id):
                    return True
        return False
    except FileNotFoundError:
        return False


def add_user(user_id, filename, message):
    """Добавляет user_id в файлесли его там еще нет """
    if not check_user_exists(user_id, filename):
        with open(filename, 'a', encoding='utf-8') as file:
            file.write(str(user_id) + '\n')
        return f"Пользователь {user_id} добавлен."
    else:
        return f"Пользователь {user_id} уже существует."


async def cmd_start(message: types.Message):
    if not check_user_exists(message.from_user.id, 'users.txt'):
        return
    await message.reply(
        "Добро пожаловать!",
        reply_markup=profile_kb
    )


#————————————————————————
#Проверка архива


async def check_session(session_path: str, proxy) -> dict:
    """
    Проверяет валидность session-файла статус 2FA 
    словарь:
      - valid: bool
      - reason: str (при невалиде)
      - two_factor: bool
      - geos: list of {ip, country, region, city}
    """
    
    #проверка на сб
    client = TelegramClient(session_path, API_ID, API_HASH, proxy=proxy,
                            device_model='Firefox 122',
                            system_version='Windows',
                            app_version='10.9.56 A',
                            system_lang_code='en-us',
                            lang_code='en')
    try:
        await client.connect()
    except telethon.errors.AuthKeyUnregisteredError:
        return {'valid': False, 'reason': 'Invalid auth key'}
    except Exception as e:
        return {'valid': False, 'reason': str(e)}

    if not await client.is_user_authorized():
        await client.disconnect()
        return {'valid': False, 'reason': 'Not authorized'}

    #2аф
    try:
        pwd = await client(telethon.functions.account.GetPasswordRequest)
        two_factor = bool(pwd.has_password)
    except Exception:
        two_factor = False

    #гео инфа
    geos = []
    try:
        auths = await client(telethon.functions.account.GetAuthorizationsRequest())
        for s in auths.authorizations:
            loc = s.ip_location
            geos.append({
                'ip': s.ip_address,
                'country': loc.country,
                'region': loc.region,
                'city': loc.city
            })
    except Exception:
        pass
    await client.disconnect()

    return {'valid': True, 'two_factor': two_factor, 'geos': geos}


def process_archive_sync(archive_path: str, user_dict: dict, batch_id: str) -> Dict:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    user = User(**user_dict)
    user.id = user_dict['id']
    results = loop.run_until_complete(handle_archive_logic(archive_path, user, batch_id, type_u='API'))
    loop.close()
    return results


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_spam_block(client):
    try:
        #logger.info("SpamBl check")
        result_text = None
        result_text_id = None
        sb_bot_entity = await client.get_entity('https://t.me/SpamBot')

        try:
            message_sent = await client.send_message('SpamBot', '/start')
            logger.info("/start в спамбот")
        except telethon.errors.rpcerrorlist.YouBlockedUserError:
            logger.warning("Заблокирован спамбот -скип")
            return None

        @client.on(events.NewMessage(from_users=sb_bot_entity.id))
        async def handler(event):
            future = asyncio.get_event_loop().create_future()
            future.set_result(event)
            try:
                await asyncio.wait_for(future, timeout=10)
            except asyncio.TimeoutError:
                logger.warning("Сбот таймаут ")
                pass

        async for msg in client.iter_messages(sb_bot_entity, reverse=True):
            result_text = msg.message
            result_text_id = msg.id

        logger.info(f"SpamBot response: {result_text}")
        await client.delete_messages(sb_bot_entity, [message_sent.id, result_text_id])
        sb_info = len(result_text.split('\n'))
        if len(result_text) > 105:
            return True
        return False if sb_info == 1 else True
    except telethon.errors.rpcerrorlist.FloodError:
        logger.info('мороз')
        return 'fr'


async def handle_archive_logic(archive_path: str, user_data: any, batch_id: str, type_u: str) -> Dict:
    """Универсальная Сложная логика обработки архива"""
    seen_hashes = set()
    seen_phones = set()
    valid_counts: Dict[str, int] = {}
    spamblock_counts: Dict[str, int] = {}
    invalid_paths = []
    user_id = user_data.telegram_id
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Price.region_code))
        allowed_codes = {row[0] for row in res.all()}
    phone_raw = None
    iso = None
    total = 0
    frozen_counts = 0
    valid_no2fa_count = 0
    valid_2fa_count = 0
    spamblock_count = 0
    dead_count = 0
    wrong_geo_count = 0
    duplicate_count = 0
    valid_no2fa_by_geo = {}
    results_details = []
    extract_dir = os.path.join(TEMP_DIR, f"extract_{batch_id}")
    os.makedirs(extract_dir, exist_ok=True)
    try:
        with zipfile.ZipFile(archive_path, 'r') as zf:
            zf.extractall(extract_dir)
    except zipfile.BadZipFile:
        raise ValueError("Invalid ZIP file")

    for root, _, files in os.walk(extract_dir):
        for fname in files:
            if not fname.lower().endswith('.session'):
                continue
            session_path = os.path.join(root, fname)
            base = os.path.splitext(fname)[0]
            info_path = os.path.join(root, base + '.json')
            data = {}

            if os.path.exists(info_path):
                try:
                    data = json.load(open(info_path, encoding='utf-8'))
                except Exception:
                    data = {}
            proxy = (socks.HTTP, '185.162.130.86', int(10000), True, 'T9FFNm2F9bwnbpnsls5x', '6BffIxsWs70Rqbeqk4pZxNrfSHqWa8G0')
            #иницилизация сессии. Получения номера, если гео есть в базе - идем дальше, если ошибка или гео нету в базе - скип
            client = TelegramClient(session_path,
                                    API_ID, API_HASH, proxy=proxy,device_model='Firefox 122',
                                    system_version='Windows',app_version='10.9.56 A',
                                    system_lang_code='en-us',lang_code='en')
            await client.connect()
            content = open(session_path, 'rb').read()
            #получение айди файла - если грузули уже то экономия ресурсов
            sha256 = hashlib.sha256(content).hexdigest()
            if sha256 in seen_hashes:
                invalid_paths.extend([session_path, info_path])
                continue
            seen_hashes.add(sha256)
            async with AsyncSessionLocal() as db:
                sess = await get_or_create_session(db, content)
            if await client.is_user_authorized():
                try:
                    me = await client.get_me()
                    phone_raw = me.phone
                    if phone_raw in seen_phones:
                        invalid_paths.extend([session_path, info_path])
                        continue
                    seen_phones.add(phone_raw)
                    async with AsyncSessionLocal() as db:
                        sess = await get_or_create_session(db, content)
                        recent_count = await db.scalar(select(func.count(Check.id)).where(Check.phone == phone_raw))
                    phone_norm = phone_raw if phone_raw.startswith('+') else '+' + phone_raw
                    try:
                        num = phonenumbers.parse(phone_norm, None)
                        region = geocoder.description_for_number(num, 'ru') or 'Неизвестно'
                        iso = phonenumbers.region_code_for_number(num)
                    except Exception:
                        region = 'Неизвестно'
                        iso = None



                    if user_data.telegram_id not in ADMIN_ID:
                        if recent_count > 0:
                            if type_u == 'API':
                                await bot.send_message(chat_id=user_id,
                                                    text=f"{get_flag_emoji(iso)} {phone_raw}:\n🔁Дубликат\nЗачислено: 0руб")
                            status = 'DUPLICATE'
                            duplicate_count += 1
                            async with AsyncSessionLocal() as db:
                                reg_code = iso if iso in allowed_codes else None
                                await create_check(db, user_data.id, sess.id, status, reg_code, None,phone_raw)
                            total += 1
                            invalid_paths.extend([session_path, info_path])
                            continue
                    info_sb = await check_spam_block(client=client)
                    if info_sb == 'fr':
                        status = 'FROZEN'
                        if type_u == 'API':
                            await bot.send_message(chat_id=user_id,text=f"{get_flag_emoji(iso)} {phone_raw}:\n❄️Мороз\nЗачислено: 0руб")
                        invalid_paths.extend([session_path, info_path])
                        frozen_counts+=1
                        continue
                    result = await client(telethon.functions.account.GetPasswordRequest())
                    if result.has_password:
                        if type_u == 'API':
                            await bot.send_message(chat_id=user_id,text=f"{get_flag_emoji(iso)} {phone_raw}:\n🔓2fa\nЗачислено: 0руб")
                        status = 'VALID_2FA'
                        valid_2fa_count+=1
                    else:
                        if iso in allowed_codes:
                            if info_sb:
                                status = 'SPAMBLOCK'
                                if type_u == 'API':
                                    await bot.send_message(user_id, f"Аккаунт {phone_raw}:\n⚠️Спамблок")
                                spamblock_count += 1
                                state_p = True
                                if iso:
                                    spamblock_counts[iso] = spamblock_counts.get(iso, 0) + 1
                                if os.path.exists(info_path): 
                                    shutil.copy(info_path, os.path.join(VALID_DIR, f"{phone_raw}.json"))
                            else:
                            
                                status = "VALID_NO2FA"
                                valid_no2fa_count += 1
                                valid_no2fa_by_geo[region] = valid_no2fa_by_geo.get(region, 0) + 1
                                valid_counts[iso] = valid_counts.get(iso, 0) + 1
                                if os.path.exists(info_path): 
                                    shutil.copy(info_path, os.path.join(VALID_DIR, f"{phone_raw}.json"))
                        else:
                            status = 'WRONG_GEO'
                            invalid_paths.extend([session_path, info_path])
                            if type_u == 'API':
                                await bot.send_message(chat_id=user_id,
                                                text=f"{get_flag_emoji(iso)} {phone_raw}:\n⛔️Другое гео\nЗачислено: 0руб")
                            wrong_geo_count+=1

                    async with AsyncSessionLocal() as db:
                        reg_code = iso if iso in allowed_codes else None
                        check = await create_check(db=db, user_id=user_data.id, session_id=sess.id,status= status,region= reg_code,price= None,phone= phone_raw)  # Изменено: user.id -> user_id
                    

                    if status in ('VALID_NO2FA', 'SPAMBLOCK'):
                        #самая сложная механника в моей жизни - переавторизация через невидимого клиента, поиск уязвимостей в офф апи. Я нашел!
                        asyncio.create_task(clone_session(proxy=proxy, client=client, api_id=API_ID, api_hash=API_HASH, pathtocodes='exported_sessions'))
                except telethon.errors.AuthKeyInvalidError or telethon.errors.AuthKeyDuplicatedError or telethon.errors.AuthKeyError or telethon.errors.AuthTokenExceptionError or telethon.errors.AuthTokenInvalid2Error or telethon.errors.AuthTokenExceptionError:
                    if type_u == 'API':
                        phone_raw = data.get('phone')
                        if phone_raw:
                            phone_norm = phone_raw if phone_raw.startswith('+') else '+' + phone_raw
                            try:
                                num = phonenumbers.parse(phone_norm, None)
                                region = geocoder.description_for_number(num, 'ru') or 'Неизвестно'
                                iso = phonenumbers.region_code_for_number(num)
                            except Exception:
                                region = 'Неизвестно'
                                iso = None
                            await bot.send_message(chat_id=user_id,
                                                        text=f"{get_flag_emoji(iso)} {phone_raw}:\n❌Мертв\nЗачислено: 0руб")
                        else:
                            await bot.send_message(chat_id=user_id,
                                                        text=f"🏴 Unknown:\n❌Мертв\nЗачислено: 0руб")
                    status = 'DEAD'
                    invalid_paths.extend([session_path, info_path])
                    dead_count += 1


                    

            else:
                if type_u == 'API':
                    phone_raw = data.get('phone')
                    if phone_raw:
                        phone_norm = phone_raw if phone_raw.startswith('+') else '+' + phone_raw
                        try:
                            num = phonenumbers.parse(phone_norm, None)
                            region = geocoder.description_for_number(num, 'ru') or 'Неизвестно'
                            iso = phonenumbers.region_code_for_number(num)
                        except Exception:
                            region = 'Неизвестно'
                            iso = None
                        await bot.send_message(chat_id=user_id,
                                                    text=f"{get_flag_emoji(iso)} {phone_raw}:\n❌Мертв\nЗачислено: 0руб")
                    else:
                        await bot.send_message(chat_id=user_id,
                                                    text=f"🏴 Unknown:\n❌Мертв\nЗачислено: 0руб")
                status = 'DEAD'
                invalid_paths.extend([session_path, info_path])
                dead_count += 1

            total += 1

            if status == 'VALID_NO2FA':
                added_amount = 0
                async with AsyncSessionLocal() as db:
                    user = await db.get(User, user_data.id)

                    price_list = await get_effective_prices(db, user_data.id)
                    valid_prices = {item[1]: item[2] for item in price_list}
                    spam_prices = {item[1]: item[3] for item in price_list}

                    for iso, cnt in valid_counts.items():
                        added_amount += valid_prices.get(iso, 0) * cnt
                    for iso, cnt in spamblock_counts.items():
                        added_amount += spam_prices.get(iso, 0) * cnt
                if type_u == 'API':
                    await bot.send_message(chat_id=user_id,
                                    text=f"{get_flag_emoji(iso)} {phone_raw}:\n✅Валид\nЗачислено: {str(added_amount)}руб")
        
        added_amount = 0
        async with AsyncSessionLocal() as db:
            user = await db.get(User, user_data.id)

            price_list = await get_effective_prices(db, user_data.id)
            valid_prices = {item[1]: item[2] for item in price_list}
            spam_prices = {item[1]: item[3] for item in price_list}

            for iso, cnt in valid_counts.items():
                added_amount += valid_prices.get(iso, 0) * cnt
            for iso, cnt in spamblock_counts.items():
                added_amount += spam_prices.get(iso, 0) * cnt

            if added_amount > 0:
                user.balance += added_amount
                db.add(user)
                await db.commit()


        lines = [f"Проверено аккаунтов: {total}", ""]
        lines.append(f"✅ Валид: {valid_2fa_count}")
        for region, cnt in valid_no2fa_by_geo.items():
            lines.append(f"    - {region}: {cnt}")
        lines += [
            f"\n🔓 2фа: {valid_2fa_count}",
            f"⚠️ Спамблок: {spamblock_count}",
            f"❌ Смерть: {dead_count}",
            f"⛔️ Другое гео: {wrong_geo_count}",
            f"❄️ Мороз: {frozen_counts}",
            f"🔁 Дубликат: {duplicate_count}",
            f"🆔 ID: {batch_id}",
        ]
        if added_amount:
            lines.append(f"\n💰 Начислено: {added_amount} руб.")

        report_text = "\n".join(lines)
        if type_u =='API':
            text_ots = 'api\n'+ f'@{user_data.username} - \n' + report_text
        else:
            text_ots = 'bot\n'+ f'@{user_data.username} - \n' + report_text

        await bot.send_message(chat_id=-4935940908, text=text_ots)

        return {
            "total": total, "valid_no2fa": valid_no2fa_count, "valid_2fa": valid_2fa_count,
            "spamblock": spamblock_count, "dead": dead_count, "wrong_geo": wrong_geo_count,
            "duplicate": duplicate_count, "added_amount": added_amount, "frozen": frozen_counts,
            "valid_no2fa_by_geo": valid_no2fa_by_geo, "invalid_paths": invalid_paths,
            "results_details": results_details
        }


async def handle_archive(message: types.Message):
    '''if message.from_user.id not in ADMIN_ID:

        if message.forward_from:
            if message.forward_from.username != 'saveonyteambot':
                await message.reply("❗️ Перешлите ZIP из бота", reply_markup=profile_kb)
                return
        else:
            await message.reply("❗️ Перешлите ZIP из бота", reply_markup=profile_kb)
            return
        if not message.document or not message.document.file_name.lower().endswith('.zip'):
            return await message.reply("❗️ Пришлите ZIP с .session и .json файлами", reply_markup=profile_kb)
    '''
    async with AsyncSessionLocal() as db:
        user = await get_or_create_user(db, message.from_user.id, message.from_user.username or '')

    await message.reply("Архив в обработке...", reply_markup=profile_kb)

    tg_file = await bot.get_file(message.document.file_id)
    archive_path = os.path.join(tempfile.gettempdir(), message.document.file_name)
    await bot.download_file(tg_file.file_path, archive_path)

    try:
        batch_id = generate_code(length=5)
        results = await handle_archive_logic(archive_path, user, batch_id, 'BOT')
        try:
            if results["invalid_paths"]:
                bad_zip = os.path.join(tempfile.gettempdir(), f"bad_{batch_id}.zip")
                with zipfile.ZipFile(bad_zip, 'w') as zf:
                    for path in results["invalid_paths"]:
                        if os.path.exists(path):
                            zf.write(path, arcname=os.path.basename(path))
                await bot.send_document(
                    message.chat.id,
                    FSInputFile(bad_zip, filename="Невалидные_сессии.zip"),
                    caption="Невалидные сессии (2FA/DEAD/неправильное GEO/дубликаты.мороз)",
                    reply_markup=profile_kb
                )
                os.remove(bad_zip)
        except:
            pass
        lines = [f"Проверено аккаунтов: {results['total']}", ""]
        lines.append(f"✅ Валид: {results['valid_no2fa']}")
        for region, cnt in results['valid_no2fa_by_geo'].items():
            lines.append(f"    - {region}: {cnt}")
        lines += [
            f"\n🔓 2фа: {results['valid_2fa']}",
            f"⚠️ Спамблок: {results['spamblock']}",
            f"❌ Смерть: {results['dead']}",
            f"⛔️ Другое гео: {results['wrong_geo']}",
            f"❄️ Мороз: {results['frozen']}",
            f"🔁 Дубликат: {results['duplicate']}",
            f"🆔 ID: {batch_id}",
        ]
        if results['added_amount']:
            lines.append(f"\n💰 Начислено: {results['added_amount']} руб.")

        report_text = "\n".join(lines)
        await message.reply(report_text, reply_markup=profile_kb)

    except ValueError as e:
        await message.reply(f"❌ Ошибка: {e}", reply_markup=profile_kb)
    finally:
        if os.path.exists(archive_path):
            os.remove(archive_path)

    # await message.reply(f"⏱ Время проверки: {start_time}\n🆔 ID: {batch_id}", reply_markup=profile_kb)


#————————————————————————
#Показ профиля
async def show_profile(message: types.Message):
    if not check_user_exists(message.from_user.id, 'users.txt'):
        return
    async with AsyncSessionLocal() as db:
        import pycountry
        user = await get_or_create_user(
            db,
            message.from_user.id,
            message.from_user.username or ''
        )
        res = await db.execute(select(Price.region_code))
        all_regions = [row[0] for row in res.all()]
        now = datetime.utcnow()
        periods = [
            ('С Е Г О Д Н Я', now - timedelta(days=1)),
            ('ЗА ВСЁ ВРЕМЯ', datetime(2000, 1, 1)),
        ]
        stats_parts = []
        for label, since in periods:
            count, breakdown = await get_stats(db, user.id, since)
            full = {code: 0 for code in all_regions}
            other = 0
            for geo, cnt in breakdown.items():
                if geo in full:
                    full[geo] = cnt
                else:
                    other += cnt
            if other:
                full['Другого гео'] = other

            stats_parts.append((label, count, full))

    header = (
        f"<b>@{user.username}</b> | <code>{user.telegram_id}</code>\n"
        f"\n📊Ваша статистика за: "
    )

    stats_lines = []
    for label, count, full in stats_parts:
        stats_lines.append(f"📊━━━{label}━━━📊")
        valid_total = await db.scalar(
            select(func.count(Check.id))
            .where(Check.user_id == user.id,
                   Check.checked_at >= since,
                   Check.status.in_(["VALID_NO2FA", "VALID_2FA"]),
                   )
        ) or 0

        spam_total = await db.scalar(
            select(func.count(Check.id))
            .where(
                Check.user_id == user.id,
                Check.checked_at >= since,
                Check.status.like("SPAMBLOCK%")
            )
        ) or 0

        dead = await db.scalar(
            select(func.count(Check.id))
            .where(
                Check.user_id == user.id,
                Check.checked_at >= since,
                Check.status == "DEAD",
            )
        ) or 0
        twof = await db.scalar(
            select(func.count(Check.id))
            .where(Check.user_id == user.id,
                   Check.checked_at >= since,
                   Check.status == "VALID_2FA",
                   )
        ) or 0
        stats_lines.append(f"\n✅ Валид: {valid_total}")
        stats_lines.append(f"⚠️ Спамблок: {spam_total}")
        stats_lines.append(f"😵 Смерть: {dead}")
        stats_lines.append(f"🔓 2фа: {twof}\n")

    stats_lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━\n💸 <b>Баланс:</b> {user.balance} руб.\n")

    quote = "<blockquote>" + "\n".join(stats_lines).rstrip() + "\n</blockquote>"
    text = header + quote
    inline_kb = [[
        InlineKeyboardButton(text="💸 Вывести", callback_data="withdraw_request")
    ]]

    kb = InlineKeyboardMarkup(inline_keyboard=inline_kb)

    await message.reply(
        text,
        parse_mode="HTML",
        reply_markup=kb
    )


# Цены
#————————————————————————

async def show_prices(message: types.Message):
    if not check_user_exists(message.from_user.id, 'users.txt'):
        return
    async with AsyncSessionLocal() as db:
        user = await get_or_create_user(
            db, message.from_user.id, message.from_user.username or ""
        )
        price_list = await get_effective_prices(db, user.id)

    temp_lines = []
    for emoji, region, normal_price, spam_price in price_list:
        country_name = country_names_ru.get(region, region)
        temp_lines.append((normal_price, f"{normal_price}₽ - {emoji} {region} - {country_name}"))
    temp_lines.sort(reverse=True)

    lines = [line for _, line in temp_lines]
    text = "Текущие цены по регионам:\n\n" + "\n".join(lines)
    await message.reply(text, reply_markup=profile_kb)


async def cmd_set_price(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 5:
        return await message.reply(
            "Использование: /set_price <код> <эмоджи> <рублей> <spamblock_руб>",
            reply_markup=profile_kb
        )
    _, region_code, emoji, default_rub_str, spamblock_rub_str = parts
    try:
        default_rub = int(default_rub_str)
        spamblock_rub = int(spamblock_rub_str)
    except ValueError:
        return await message.reply(
            "Цены должны быть целыми числами.",
            reply_markup=profile_kb
        )

    async with AsyncSessionLocal() as db:
        await set_default_price(
            db,
            region_code,
            emoji,
            default_rub,
            spamblock_rub
        )

    await message.reply(
        f"Глобальные цены для {region_code} установлены:\n"
        f"  • Обычные: {emoji} – {default_rub} ₽\n"
        f"  • За SPAMBLOCK: {spamblock_rub} ₽",
        reply_markup=profile_kb
    )


async def cmd_set_user_price(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 5:
        return await message.reply(
            "Использование: /set_user_price <telegram_id> <код_региона> "
            "<рублей> <spamblock_рублей>",
            reply_markup=profile_kb
        )
    _, tg_id_str, region_code, price_rub_str, spamblock_rub_str = parts
    try:
        tg_id = int(tg_id_str)
        price_rub = int(price_rub_str)
        spamblock_rub = int(spamblock_rub_str)
    except ValueError:
        return await message.reply(
            "Telegram ID и цены должны быть целыми числами.",
            reply_markup=profile_kb
        )

    async with AsyncSessionLocal() as db:
        user = await get_or_create_user(db, tg_id, username="")
        await set_user_price(db, user.id, region_code, price_rub, spamblock_rub)

    await message.reply(
        f"Переопределённые цены для @{user.username or user.telegram_id}:\n"
        f"  • Обычные: {price_rub} ₽\n"
        f"  • SPAMBLOCK: {spamblock_rub} ₽",
        reply_markup=profile_kb
    )


async def cmd_delete_region(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2:
        return await message.reply(
            "Использование: /del_region <код_региона>",
            reply_markup=profile_kb
        )
    _, region_code = parts
    async with AsyncSessionLocal() as db:
        await delete_region(db, region_code)
    await message.reply(
        f"Регион {region_code} и все его переопределения удалены.",
        reply_markup=profile_kb
    )




async def on_withdraw_request(callback: types.CallbackQuery):
    async with AsyncSessionLocal() as db:
        user = await get_or_create_user(
            db,
            callback.from_user.id,
            callback.from_user.username or ""
        )
        amount = user.balance
        q = await db.execute(select(MinWithdrawal.min_with))
        all_regions = [row[0] for row in q.all()]
        print(all_regions)
        if amount < int(all_regions[0]):
            return await callback.answer(f"❌ Вывод доступен с {all_regions[0]}Р", show_alert=True)
        w = await request_withdrawal(db, user, amount)
    await bot.send_message(chat_id=-4935940908,
                           text=f'@{callback.from_user.username} - \n новый запрос на {amount}\nID: {w.id}')
    await callback.answer(
        f"Запрос на вывод {amount}₽ создан (ID {w.id}).",
        show_alert=True
    )

    done_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💸 Запрос создан", callback_data="noop")]
        ]
    )
    await callback.message.edit_reply_markup(reply_markup=done_kb)


async def cmd_list_withdrawals(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        return

    async with AsyncSessionLocal() as db:
        pend = await list_pending_withdrawals(db)
        if not pend:
            await message.reply("Нет заявок на вывод.")
            return

        lines = []
        for w in pend:
            username_or_id = w.user.username or w.user.telegram_id
            lines.append(f"ID {w.id}: @{username_or_id} — {w.amount}₽")

    await message.reply("\n".join(lines))


async def cmd_approve_withdrawal(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("Использование: /approve_withdrawal <ID>")
    username = message.from_user.username or "unknown"
    userid = message.from_user.id
    wid = int(parts[1])
    async with AsyncSessionLocal() as db:
        w = await change_withdrawal_status(db, wid, WithdrawStatus.APPROVED)
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not w:
        return await message.reply("Запрос не найден.")

    async with aiofiles.open('withdrawal_stats.csv', 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        await f.write(f"approve,{date},{username},{userid},{w.amount}\n")
    await message.reply(f"Запрос {wid} одобрен.")


async def cmd_reject_withdrawal(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.reply("Использование: /reject_withdrawal <ID>")

    wid = int(parts[1])
    async with AsyncSessionLocal() as db:
        w = await change_withdrawal_status(db, wid, WithdrawStatus.REJECTED)
        username = w.user or "unknown"
        userid = w.user_id
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if w:
            async with aiofiles.open('withdrawal_stats.csv', 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                await f.write(f"rejec,{date},{username},{userid},{w.amount}\n")
            user = await db.get(User, w.user_id)
            user.balance += w.amount
            db.add(user)
            await db.commit()

    if not w:
        return await message.reply("Запрос не найден.")
    await message.reply(f"Запрос {wid} отклонён и сумма возвращена.")


logger = logging.getLogger(__name__)


async def cmd_export_stats(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        return

    text = message.text or ""
    parts = text.split(maxsplit=1)

    if len(parts) == 1:
        return await message.reply(
            "Использование:\n"
            "/export_stats day   — за последние 24 ч\n"
            "/export_stats week  — за последнюю неделю\n"
            "/export_stats month — за последние 30 дней\n"
            "/export_stats all   — за всё время",
            reply_markup=profile_kb
        )

    period = parts[1].strip().lower()
    now = datetime.utcnow()
    if period == "day":
        since = now - timedelta(days=1)
    elif period == "week":
        since = now - timedelta(weeks=1)
    elif period == "month":
        since = now - timedelta(days=30)
    elif period == "all":
        since = datetime(1970, 1, 1)
    else:
        return await message.reply(
            "Неверный период. Выберите day, week, month или all.",
            reply_markup=profile_kb
        )

    rows = []
    async with AsyncSessionLocal() as db:
        users = (await db.execute(select(User))).scalars().all()
        for user in users:
            valid_total = await db.scalar(
                select(func.count(Check.id))
                .where(
                    Check.user_id == user.id,
                    Check.checked_at >= since,
                    Check.status.in_(["VALID_NO2FA", "VALID_2FA"])
                )
            ) or 0

            spam_total = await db.scalar(
                select(func.count(Check.id))
                .where(
                    Check.user_id == user.id,
                    Check.checked_at >= since,
                    Check.status.like("SPAMBLOCK%")
                )
            ) or 0

            dead = await db.scalar(
                select(func.count(Check.id))
                .where(
                    Check.user_id == user.id,
                    Check.checked_at >= since,
                    Check.status == "DEAD"
                )
            ) or 0

            breakdown_res = await db.execute(
                select(Check.region, func.count(Check.id))
                .where(
                    Check.user_id == user.id,
                    Check.checked_at >= since,
                    Check.status != "DUPLICATE"
                )
                .group_by(Check.region)
            )
            breakdown = ";".join(
                f"{(reg or 'Неизвестно')}:{cnt}"
                for reg, cnt in breakdown_res.all()
            )

            rows.append([
                user.username or "",
                user.telegram_id,
                valid_total,
                spam_total,
                dead,
                breakdown
            ])

    tmp = tempfile.NamedTemporaryFile("w+", delete=False, suffix=".csv")
    writer = csv.writer(tmp)
    writer.writerow([
        "Login", "TelegramID",
        "ValidTotal", "SpamTotal", "Dead",
        "RegionBreakdown"
    ])
    writer.writerows(rows)
    tmp.flush()
    tmp.close()

    await message.reply_document(
        FSInputFile(tmp.name),
        caption=f"Экспорт статистики ({period})",
        reply_markup=profile_kb
    )
    os.unlink(tmp.name)


async def cmd_export_sessions(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
            return
    inline_kb = [
        [InlineKeyboardButton(text="🔙Назад", callback_data="back")],
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=inline_kb)
    result = count_iso_codes('app/bot/src/db.db')
    one_mess = await bot.send_message(message.from_user.id,text=f'<b>Держится аккаунтов:\n {result}</b>\n\nПример:\n"RU" - экспорт рф аккаунтов\n"ALL" - экспорт всех сессий\nВедите ISO-код страны аккаунтов для экспорта.',parse_mode="HTML",reply_markup=reply_markup)
    await state.set_state(ApplyUserForm.waiting_iso_code)
    await state.update_data(prompt_message_id=one_mess.message_id)
async def apply_user(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply('используйте  /apply_user userid')

    tf = add_user(parts[1], 'users.txt', message)
    await message.reply(tf)


async def del_user(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        return

    parts = message.text.split()
    print(parts)
    if len(parts) != 2:
        await message.reply('используйте  /del_user userid')

    tf = remove_user(parts[1], 'users.txt', message)
    await message.reply(tf)


async def set_min_withdraw(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        return

    parts = message.text.split()
    print(parts)
    if len(parts) != 2:
        await message.reply('используйте  /set_min_withdraw min')

    async with AsyncSessionLocal() as db:
        stmt = select(MinWithdrawal)
        result = await db.execute(stmt)
        exist_r = result.scalar_one_or_none()
        if exist_r:
            await db.delete(exist_r)
        new_min = MinWithdrawal(min_with=int(parts[1]))
        db.add(new_min)
        await db.commit()

    await message.reply(f'Минимальный вывод установлен на {parts[1]}')


async def cmd_set_max(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply('используйте  /set_max max')

    async with AsyncSessionLocal() as db:
        stmt = select(MaxAccs)
        result = await db.execute(stmt)
        exist_r = result.scalar_one_or_none()

        if exist_r:
            await db.delete(exist_r)

        new_max_accs = MaxAccs(max_accs=int(parts[1]))
        db.add(new_max_accs)

        await db.commit()

    await message.reply(f'Лимит аккаунтов установлен на {parts[1]}')


async def broadcast_command(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        return

    broadcast_text = message.text[len('/broadcast '):].strip()
    if not broadcast_text:
        await message.answer("Пожалуйста, укажите текст для рассылки после команды /broadcast.")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    if not users:
        await message.answer("В базе данных нет пользователей.")
        return

    success_count = 0
    error_count = 0

    for user in users:
        try:
            await bot.send_message(chat_id=user.telegram_id, text=broadcast_text)
            success_count += 1
            await asyncio.sleep(0.05)  # Задержка для соблюдения лимитов Telegram
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {user.telegram_id}: {e}")
            error_count += 1

    await message.answer(
        f"Рассылка завершена!\n"
        f"Успешно отправлено: {success_count} пользователям\n"
        f"Ошибок: {error_count}"
    )


async def cmd_export_withdrawal_stats(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        return

    withdrawal_stats_file = "withdrawal_stats.csv"

    if not os.path.exists(withdrawal_stats_file):
        await message.reply("❌ Файл withdrawal_stats.csv не найден.")
        return

    try:
        await message.reply_document(
            FSInputFile(withdrawal_stats_file),
            caption="📊 Статистика выводов",
            reply_markup=profile_kb
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке файла withdrawal_stats.csv: {e}")
        await message.reply("❌ Ошибка при экспорте файла. Обратитесь к администратору.")


async def get_max(message: types.Message):
    if not check_user_exists(message.from_user.id, 'users.txt'):
        return

    async with AsyncSessionLocal() as db:
        q = await db.execute(select(MaxAccs.max_accs))
        current_max_with = [row[0] for row in q.all()]
    await message.reply(f"До конца приемки осталось {str(current_max_with[0])} аккаунтов", reply_markup=profile_kb)


async def cmd_info(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        return
    await message.reply('''
/apply_user [user_id] - добавить типа
/del_user [user_id] - удалить типа
/set_price <код> <эмоджи> <рублей> <spamblock_руб>
/del_region - удалить ну бля тут понятно
/list_withdrawals - список запросов на вывод
/approve_withdrawal id - принять вывод
/reject_withdrawal id - отменить вывод
/export_stats - стата
/export_sessions - экспорт сессий
/set_min_withdraw - мин вывод
/export_withdrawal_stats - тут пон да
    ''')


class ApplyUserForm(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_user_id_del = State()
    waiting_iso_code = State()
    waiting_for_broadcast = State()
    waiting_set_max = State()
    waiting_set_min = State()
    waiting_set_price_global = State()
    waiting_set_price_user  =State()
    waiting_set_price_spamblock = State()
    waiting_set_price_smapblock1 = State()
    waiting_del_region = State()


@dp.message(ApplyUserForm.waiting_iso_code)
async def process_user_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await bot.edit_message_text(chat_id=message.from_user.id,message_id=data.get("prompt_message_id"), text='сессии сохраняются, подождите...')
    await bot.delete_message(chat_id=message.from_user.id, message_id=message.message_id)
    sess = get_records('app/bot/src/db.db', message.text)
    proxy = (socks.HTTP, '185.162.130.86', int(10000), True, 'T9FFNm2F9bwnbpnsls5x', '6BffIxsWs70Rqbeqk4pZxNrfSHqWa8G0')
    for line in sess:
        asyncio.create_task(accept_session(line,proxy,API_ID,API_HASH,'exported_sessions/valid',password=None))
    await asyncio.sleep(20)
    valid_bases = {
        os.path.splitext(f)[0]
        for f in os.listdir('exported_sessions\\valid')
        if f.endswith('.session')
    }
    spam_bases = {
        os.path.splitext(f)[0]
        for f in os.listdir('exported_sessions\\spam')
        if f.endswith('.session')
    }

    if not valid_bases and not spam_bases:
        return await bot.send_message(chat_id=message.from_user.id,text="ℹ️ Пока нет ни одной сохранённой сессии для экспорта.")

    def make_zip(source_dir, bases: set[str], zip_name: str):
        zip_path = os.path.join(TEMP_DIR, zip_name)
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for base in bases:
                # .session
                sess_path = os.path.join(source_dir, f"{base}.session")
                if os.path.exists(sess_path):
                    zf.write(sess_path, arcname=f"{base}.session")
                # .json
                json_path = os.path.join(source_dir, f"{base}.json")
                if os.path.exists(json_path):
                    zf.write(json_path, arcname=f"{base}.json")
                if os.path.exists(f'exported_sessions\\exported\\{base}.json'):
                    os.remove(f'exported_sessions\\exported\\{base}.json')
                if os.path.exists(f'exported_sessions\\exported\\{base}.session'):
                    os.remove(f'exported_sessions\\exported\\{base}.session')

                shutil.move(sess_path, 'exported_sessions\\exported')
                shutil.move(json_path, 'exported_sessions\\exported')
        return zip_path

    # экспорт валидных
    if valid_bases:

        zip_valid = make_zip(VALID_DIR, valid_bases, "valid_sessions.zip")
        await bot.send_document(
            chat_id=message.from_user.id,
            document=FSInputFile(zip_valid),
            caption="🟢 Валидные сессии и JSON"
        )
        os.remove(zip_valid)
    else:
        await message.reply("ℹ️ Нет валидных сессий для экспорта.")

    for d, bases in ((VALID_DIR, valid_bases), (SPAM_DIR, spam_bases)):
        for base in bases:
            for ext in ('.session', '.json'):
                path = os.path.join(d, f"{base}{ext}")
                if os.path.exists(path):
                    os.remove(path)
    

    await state.clear()
# /start
dp.message.register(cmd_start, Command("start"))
# добавление юсера
dp.message.register(apply_user, Command("apply_user"))
# удаление юсера
dp.message.register(del_user, Command("del_user"))
# рассылка
dp.message.register(broadcast_command, Command("broadcast"))
# Обработка архива
dp.message.register(handle_archive, F.document)
# Кнопка профиль
dp.message.register(show_profile, F.text == "👤 Профиль")
# Кнопка цены
dp.message.register(show_prices, F.text == "💰 Цены")

dp.message.register(get_max, F.text == "💸 Информация о приемке")

dp.message.register(cmd_set_max, Command("set_max"))

#Установка цены (только для админа)
dp.message.register(cmd_set_price, Command("set_price"))
#Установка пользовательской цены (только для админа)
dp.message.register(cmd_set_user_price, Command("set_user_price"))
# Удаление региона (только для админа)
dp.message.register(cmd_delete_region, Command("del_region"))
# Запрос вывода денег
dp.callback_query.register(on_withdraw_request, F.data == "withdraw_request")
# Список заявок на вывод (только для админа)
dp.message.register(cmd_list_withdrawals, Command("list_withdrawals"))
# Одоброение вывода (только для админа)
dp.message.register(cmd_approve_withdrawal, Command("approve_withdrawal"))
# Отклонение вывода (только для админа)
dp.message.register(cmd_reject_withdrawal, Command("reject_withdrawal"))
#Экспорт статистики (только для админа)
dp.message.register(cmd_export_stats, Command("export_stats"))
#Выгрузка сессий (только для админа)
dp.message.register(cmd_export_sessions, Command("export_sessions"))
#установка мин вывода
dp.message.register(set_min_withdraw, Command("set_min_withdraw"))
#экспорт статы по выводам
dp.message.register(cmd_export_withdrawal_stats, Command("export_withdrawal_stats"))
dp.message.register(cmd_info, Command("cmd"))


#————————————————————————
#Инициализация БД и запуск
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
