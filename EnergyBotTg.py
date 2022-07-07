import sqlite3
import datetime
from aiogram.types.message import ContentType, ContentTypes
from aiogram.types.successful_payment import SuccessfulPayment
from aiohttp_socks import SocksConnector
from aiogram.dispatcher.filters.state import State, StatesGroup
from contextlib import closing
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram import Bot, types, exceptions
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton, pre_checkout_query, reply_keyboard
from aiogram.utils.exceptions import BotBlocked

class Form(StatesGroup):
   peremennaya = State()
   start = State()

ytoken="payment:token"
bot = Bot("token bot")
storage = MemoryStorage()
dp = Dispatcher(bot,storage=storage)

button_check = KeyboardButton("Посмотреть количество")
button_add = KeyboardButton("Добавить")
button_change_nick = KeyboardButton("Изменить ник")
button_top = KeyboardButton("Показать топ")
button_sub0 = KeyboardButton("Подписка")
start_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(button_check,button_add,button_change_nick,button_top,button_sub0)
sub_inline_markup = InlineKeyboardMarkup(row_width=1)
button_sub = InlineKeyboardButton(text="Час - 300р.", callback_data="sub")
sub_inline_markup.insert(button_sub)

@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    await message.reply("Дарова, смотри что умею",reply_markup=start_keyboard)
    with closing(sqlite3.connect("UsersTG.db")) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECt id FROM Users")
        records = cursor.fetchall()
        flag = 1

        for row in records:
            if row[0] == message.from_user.id:
                flag = 0
                break

        if flag == 1:
            cursor.execute("INSERT INTO Users VALUES (?,?,?,?,?,?)",(message.from_user.id, datetime.datetime.now().strftime('%d/%m/%Y'), 0, message.from_user.first_name,False,None))
            connection.commit()
            flag = 0
                
@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
    await message.reply("Смотри чем помочь могу")

@dp.message_handler(content_types="text")
async def check_message(message: types.Message):
    try: 
        if message.text == "Изменить ник":
            await message.reply("Введи ник",reply_markup=types.ReplyKeyboardRemove())
            await Form.peremennaya.set()

        if message.text == "Добавить":
            await message.reply("Добавлен")
            with closing(sqlite3.connect("UsersTG.db")) as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT count FROM Users WHERE id = ?",(message.from_user.id,))  
                count = cursor.fetchone()

                try:
                    cursor.execute("UPDATE Users SET count = ? WHERE id = ?",(count[0] +1,message.from_user.id,))
                    connection.commit()

                except:
                    cursor.execute("INSERT INTO Users VALUES (?,?,?,?,?,?)",(message.from_user.id, datetime.datetime.now().strftime('%d/%m/%Y'), 1, message.from_user.first_name,False,None))
                    connection.commit()

        if message.text == "Посмотреть количество":
            with closing(sqlite3.connect("UsersTG.db")) as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT count FROM Users WHERE id = ?",(message.from_user.id,))
                count = cursor.fetchone()

                try:
                    s_text = "Всего " + str(count[0])

                except:
                    cursor.execute("INSERT INTO Users VALUES (?,?,?,?,?,?)",(message.from_user.id, datetime.datetime.now().strftime('%d/%m/%Y'), 1, message.from_user.first_name,False,None))
                    connection.commit()

                finally: 
                    cursor.execute("SELECT count FROM Users WHERE id = ?",(message.from_user.id,))
                    count = cursor.fetchone()
                    s_text = "Всего " + str(count[0])
                    await message.reply(s_text)

        if message.text == "Показать топ":
            with closing(sqlite3.connect("UsersTG.db")) as connection:
                cursor = connection.cursor()
                cursor.execute("SELECT count,Name,Nick FROM Users ORDER BY count DESC")
                top=cursor.fetchall()
                mess = ""
                i = 1

                for row in top:
                    if row[1] == None:
                        continue

                    if row[2] == None:
                        mess = mess + str(i) + ". " + row[1] + ": " + str(row[0]) + "\n"
                        i = i + 1
                    else:
                        mess = mess + str(i) + ". " + row[2] + ": " + str(row[0]) + "\n"
                        i = i + 1
                await message.reply(mess)

        if message.text == "Подписка":
            await bot.send_message(message.from_user.id, "Купи себе подписку", reply_markup=sub_inline_markup)

    except BotBlocked:
        pass



@dp.message_handler(state=Form.peremennaya)
async def change_name(message: types.Message,state: FSMContext):
    await state.update_data(nick=message.text,idus=message.from_user.id)
    data= await state.get_data()

    with closing(sqlite3.connect("UsersTG.db")) as connection:
        cursor = connection.cursor()

        try:
            cursor.execute("UPDATE Users SET Nick = ? WHERE id = ?",(data["nick"],data["idus"],))
            connection.commit()

        except:
            cursor.execute("INSERT INTO Users VALUES (?,?,?,?,?,?)",(message.from_user.id, datetime.datetime.now().strftime('%d/%m/%Y'), 1, message.from_user.first_name,False,data["nick"]))
            connection.commit()

        finally:
            await message.reply("Ник изменен",reply_markup=start_keyboard)
            await state.finish()

@dp.callback_query_handler(text="sub")
async def sub(call: types.CallbackQuery):
    await bot.delete_message(call.from_user.id, call.message.message_id)
    await bot.send_invoice(chat_id=call.from_user.id, title="Оформление подписки", description="Подписка", payload="submonth", provider_token=ytoken, currency="RUB", start_parameter="test_bot", prices=[{"label": "Руб", "amount": "30000"}])

@dp.pre_checkout_query_handler()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message_handler(content_types=ContentType.SUCCESSFUL_PAYMENT)
async def process_pay(message: types.Message):
    if message.successful_payment.invoice_payload == "submonth":
        await bot.send_message(message.from_user.id, "Подписка доступна на 1 час")

if __name__ == '__main__':
    executor.start_polling(dp)
