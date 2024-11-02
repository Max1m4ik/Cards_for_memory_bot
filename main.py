import telebot
from telebot import types
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from config import TOKEN

# from functions import *
from itertools import groupby
import sqlite3 as sq

# from datetime import datetime
# from UTC_LIST import utc_to_timezone
#import schedule
import time
import threading
import string
import random

only_one = 0
bot = telebot.TeleBot(TOKEN)
correct = 0
stage = "null"
my_message = 1
user_id = 0
question_counter = 1
check_stage = 0
current_set = ""
text = ""
reminder_active = False
interval_minutes = 0
reminder_set = ""
choose_set_for = 0
target_epoch_time = 0
add_class_stage = 1


def update():
    global col_of_set
    global col_of_q
    global user_id
    global current_set
    with sq.connect("cards.db") as con:
        cur = con.cursor()
        cur.execute(
            """SELECT question FROM cards WhERE user_id = ? AND set_name = ?""",
            (user_id, current_set[0]),
        )
        questions = cur.fetchall()
        unique_questions = [el for el, _ in groupby(questions)]
        col_of_q = len(unique_questions)
        for i in range(1, col_of_q + 1):
            q = str(unique_questions[i - 1])[2:-3]
            cur.execute(
                """UPDATE cards SET number = ? WHERE question = ? AND user_id = ? AND set_name = ?""",
                (i, q, user_id, current_set[0]),
            )

def update_classes():
    global classes_with_me
    global my_classes
    global all_classes
    with sq.connect("students.db") as con:
        cur = con.cursor()
        cur.execute(f"SELECT code FROM students WHERE student_id = {user_id}")
        classes_with_me = cur.fetchall()
    with sq.connect("classes.db") as con:
        cur = con.cursor()
        cur.execute(f"SELECT code FROM classes WHERE teacher = {user_id}")
        my_classes = cur.fetchall()
        cur.execute(f"SELECT code FROM classes")
        all_classes = cur.fetchall()


def update_sets():
    global col_of_set
    global sets
    global user_id
    with sq.connect("sets.db") as con:
        cur = con.cursor()
        print(f"user_id: {user_id}, type: {type(user_id)}")
        cur.execute(f"SELECT set_name FROM sets WHERE user_id = {user_id}")
        set = cur.fetchall()
        sets = set
        print(set)
        unique_set = [el for el, _ in groupby(set)]
        sets = unique_set
        print(unique_set, "unique_set")
        print(sets, "sets")
        col_of_set = len(unique_set)
        print(unique_set)
        
@bot.message_handler(commands=['join'])
def handle_join_command(message):
    # Извлечение параметра из команды
    command, param = message.text.split(sep="_")
    user_id = message.from_user.id
    with sq.connect("students.db") as con:
        cur = con.cursor()
        cur.execute(f"INSERT OR UPDATE INTO students (student_id, code) VALUES ({user_id}, {param})")
    bot.reply_to(message, f"Вы присоединились к классу.")


def add(question, answer):
    global current_set
    with sq.connect("cards.db") as con:
        cur = con.cursor()
        cur.execute(
            """SELECT question FROM cards WhERE user_id = ? AND set_name = ?""",
            (user_id, current_set[0]),
        )
        questions = cur.fetchall()
        unique_questions = [el for el, _ in groupby(questions)]
        col_of_q = len(unique_questions)
    with sq.connect("cards.db") as con:
        cur = con.cursor()
        cur.execute(
            f"""INSERT INTO cards (user_id, number, set_name, question, answer) VALUES (? , ? , ? , ?, ?)""",
            (user_id, col_of_q + 1, current_set[0], question, answer),
        )

def generate_short_unique_key(length=5):
    # Определяем набор символов: буквы и цифры
    characters = string.ascii_letters + string.digits
    # Генерируем случайный ключ заданной длины
    return ''.join(random.choice(characters) for _ in range(length))

def add_set(name):
    global sets
    global current_set
    sets = []  # - возможна ошибка
    with sq.connect("sets.db") as con:
        cur = con.cursor()
        cur.execute(
            f"""INSERT INTO sets (user_id, set_name) VALUES (? , ?)""", (user_id, name)
        )
    sets.append(name)
    current_set = name
    
def add_class(message, name):
    update_classes()
    new_key = generate_short_unique_key()
    while new_key in all_classes:
        new_key = generate_short_unique_key()
    with sq.connect("classes.db") as con:
        cur = con.cursor()
        cur.execute(f"INSERT INTO classes (teacher, class_name, code) VALUES (?, ?, ?)", (user_id, name, new_key))
    bot.send_message(message.chat.id, "Для того чтобы дети присоеденились к вашему классу отправте им ссылку:")
    bot.send_message(message.chat.id, f"https://t.me/Cards_for_memory_bot?start=join_{new_key}")
    
    


def quest(number):
    try:
        global question
        global current_set
        update_sets()
        with sq.connect("cards.db") as con:
            cur = con.cursor()
            cur.execute(
                f"""SELECT question FROM cards WHERE number = ? AND user_id = ? AND set_name = ?""",
                (number, user_id, current_set[0]),
            )
            question = cur.fetchall()
            question = str(question[0])[2:-3]
    except IndexError:
        pass


def answ(number):
    try:
        global r_answer
        with sq.connect("cards.db") as con:
            cur = con.cursor()
            cur.execute(
                f"""SELECT answer FROM cards WHERE number = ? AND user_id = ? AND set_name = ?""",
                (number, user_id, current_set[0]),
            )
            r_answer = cur.fetchall()
            r_answer = str(r_answer[0])[2:-3]
    except IndexError:
        pass


def menu(message):
    global my_message
    main_kb = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(text="Проверить знания", callback_data="check")
    btn2 = types.InlineKeyboardButton(
        text="Редактировать каточки", callback_data="edit"
    )
    btn3 = types.InlineKeyboardButton(text="Выход", callback_data="exit_to_set_menu")
    main_kb.add(btn1)
    main_kb.add(btn2)
    main_kb.add(btn3)
    my_message = bot.send_message(
        message.chat.id, "Что вы хотите сделать? ", reply_markup=main_kb
    )


def set_menu(message):
    set_menu_kb = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(text="Выбрать набор", callback_data="choose_set")
    btn2 = types.InlineKeyboardButton(text="Добавить набор", callback_data="add_set")
    btn3 = types.InlineKeyboardButton(text="Удалить набор", callback_data="del_set")
    set_menu_kb.add(btn1)
    set_menu_kb.add(btn2)
    set_menu_kb.add(btn3)
    bot.send_message(message.chat.id, "Выберите действие", reply_markup=set_menu_kb)


def set_intervals_on(current_set, user_id, message):
    global choose_set_for
    choose_set_for = 1
    update_sets()
    if current_set not in sets:
        choose_set_kb = types.InlineKeyboardMarkup()
        choose_set_btn = types.InlineKeyboardButton(
            text="Выбрать набор", callback_data="choose_set"
        )
        choose_set_btn2 = types.InlineKeyboardButton(
            text="Выход", callback_data="exit_to_main"
        )
        choose_set_kb.add(choose_set_btn)
        choose_set_kb.add(choose_set_btn2)
        bot.send_message(
            message.chat.id, "Пожалуйста выберите набор ", reply_markup=choose_set_kb
        )
    else:
        with sq.connect("intervals.db") as con:
            cur = con.cursor()
            cur.execute(
                f"""DELETE FROM intervals WHERE user_id = ? AND set_name = ?""",
                (user_id, current_set[0]),
            )
            cur.execute(
                f"""INSERT OR IGNORE INTO intervals (user_id, set_name, value) VALUES (? , ? , ?)""",
                (user_id, current_set[0], 1),
            )
        bot.send_message(
            message.chat.id,
            "Отлично! Для начала напоминаний пройдите тестирование в этом наборе чтобы определить интервал повторения",
        )
        menu(message)
        choose_set_for = 0


def set_intervals_off(current_set, user_id, message):
    global choose_set_for
    choose_set_for = 2
    update_sets()
    if current_set not in sets:
        choose_set_kb = types.InlineKeyboardMarkup()
        choose_set_btn = types.InlineKeyboardButton(
            text="Выбрать набор", callback_data="choose_set"
        )
        choose_set_btn2 = types.InlineKeyboardButton(
            text="Выход", callback_data="exit_to_main"
        )
        choose_set_kb.add(choose_set_btn)
        choose_set_kb.add(choose_set_btn2)
        bot.send_message(
            message.chat.id, "Пожалуйста выберите набор ", reply_markup=choose_set_kb
        )
    else:
        with sq.connect("intervals.db") as con:
            cur = con.cursor()
            cur.execute(
                f"""DELETE FROM intervals WHERE user_id = ? AND set_name = ?""",
                (user_id, current_set[0]),
            )
            cur.execute(
                f"""INSERT OR REPLACE INTO intervals (user_id, set_name, value) VALUES (? , ? , ?)""",
                (user_id, current_set[0], 0),
            )
            bot.send_message(message.chat.id, "Напоминания для этого набора отключены")
        choose_set_for = 0


def calculate_next_interval(correct_percentage):
    # Пример интервалов на основе процента правильных ответов
    if correct_percentage >= 90:
        return 1*60 # 24 часа
    elif correct_percentage >= 75:
        return 2*60  # 12 часов
    elif correct_percentage >= 50:
        return 2*60  # 6 часов
    else:
        return 4*60  # 3 часа


def send_reminder(chat_id, current_set):
    global reminder_active
    global reminder_set

    kb = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(
        text="Проверить знания", callback_data="check_from_reminder"
    )
    kb.add(btn1)
    reminder_set = current_set
    bot.send_message(
        chat_id, f"Пора повторить материал! В наборе {current_set[0]}", reply_markup=kb
    )
    reminder_active = False

def run_reminder(chat_id, current_set):
    global reminder_active  # Объявляем переменную как глобальную
    global target_epoch_time
        # Бесконечный цикл, который будет проверять текущее время
    while True:
        current_time = time.time()
        if current_time == target_epoch_time:
            #target_epoch_time = time.time() + 2 #60*60*24
            send_reminder(chat_id, current_set)
        # Задержка, чтобы не нагружать процессор
        time.sleep(20)


def start_reminder_thread(chat_id, correct_percentage, current_set):
    global target_epoch_time
    global only_one
    global interval_minutes
    if only_one == 0:
        interval_minutes = calculate_next_interval(correct_percentage)
        target_epoch_time = time.time() + interval_minutes
        print(f"Следующие напоминание через {interval_minutes} минут")
        #reminder_active = True
        # schedule.every(interval_minutes).minutes.do(send_reminder, chat_id=chat_id)
        reminder_thread = threading.Thread(
            target=run_reminder, args=(chat_id, current_set)
        )
        reminder_thread.start()
        only_one += 1
    else:
        #reminder_active = True
        interval_minutes = calculate_next_interval(correct_percentage)
        target_epoch_time = time.time() + interval_minutes
        #reminder_thread = threading.Thread(
        #    target=run_reminder, args=(chat_id, current_set)
        #)
        #reminder_thread.start()
        print(f"Следующие напоминание через {interval_minutes} минут")
        print("второй путь")


def edit_menu(message):
    edit_menu = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(text="Добавить карточки", callback_data="add")
    btn2 = types.InlineKeyboardButton(text="Удалить карточки", callback_data="delite")
    btn3 = types.InlineKeyboardButton(text="Выход", callback_data="finish_editing")
    edit_menu.add(btn1)
    edit_menu.add(btn2)
    edit_menu.add(btn3)
    bot.send_message(
        chat_id=message.chat.id,
        text="Выберите что вы будите делать: ",
        reply_markup=edit_menu,
    )


@bot.message_handler(commands=["start"])
def start(message):
    global user_id
    global col_of_set
    user_id = message.from_user.id
    # update()
    update_sets()
    print(col_of_set)
    if col_of_set + 1 > 1:
        set_menu(message)
    else:
        add_kb = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton(text="Создать набор", callback_data="add_set")
        btn2 = types.InlineKeyboardButton(text="Выход", callback_data="exit_to_main")
        add_kb.add(btn1, btn2)
        bot.send_message(
            message.chat.id,
            "У вас не ни одного набора, создайте его",
            reply_markup=add_kb,
        )

@bot.message_handler(commands=["add_class"])
def add_class_command(message):
    global stage
    global add_class_stage
    stage = "add_class"
    bot.reply_to(message, "Введите цифру и номер класса:")
    
@bot.message_handler(commands=["reminder_on"])
def start(message):
    set_intervals_on(current_set, user_id, message)


@bot.message_handler(commands=["reminder_off"])
def start(message):
    set_intervals_off(current_set, user_id, message)


@bot.message_handler(content_types=["text"])
def chek_text(message):
    global stage
    global question_for_add
    global answer_for_add
    global answer
    global r_answer
    global correct
    global check_stage
    global col_of_q
    global question_counter
    global sets
    global user_id
    global current_set
    # print(stage)
    user_id = message.from_user.id
    global choose_set_for
    if stage == "choose":
        current_set = sets[int(message.text) - 1]
        if choose_set_for == 1:
            set_intervals_on(current_set, user_id, message)
        elif choose_set_for == 2:
            set_intervals_off(current_set, user_id, message)
        else:
            menu(message)

    elif stage == "add_set":
        add_set(message.text)
        bot.send_message(message.chat.id, "Хранилеще успешно созданно!")
        menu(message)
        
    elif stage == "add_class":
        if add_class_stage == 1:
            add_class(message, message.chat.id)
        

    elif stage == "del_set":
        if int(message.text) <= col_of_set:
            set_for_del = str(sets[int(message.text) - 1])[2:-3]
            with sq.connect("sets.db") as con:
                cur = con.cursor()
                cur.execute(
                    f"""DELETE FROM sets WHERE set_name = ? AND user_id = ?""",
                    (set_for_del, user_id),
                )
                sets.remove(sets[int(message.text) - 1])
            with sq.connect("cards.db") as con:
                cur = con.cursor()
                cur.execute(
                    f"""DELETE FROM cards WHERE set_name = ? AND user_id = ?""",
                    (set_for_del, user_id),
                )
            bot.send_message(message.chat.id, "Набор успешно удален")
            start(message)
        else:
            del_set_kb = types.InlineKeyboardMarkup()
            btn1 = types.InlineKeyboardButton(
                text="Выход", callback_data="exit_to_set_menu"
            )
            btn2 = types.InlineKeyboardButton(
                text="Удалить набор", callback_data="del_set"
            )
            del_set_kb.add(btn1, btn2)
            bot.send_message(
                message.chat.id,
                "Такого набора у вас нет, выйдите в меню или удалите другой набор",
                reply_markup=del_set_kb,
            )

    elif stage == "check":
        for i in range(2):
            if check_stage == 1:
                update()
                answ(question_counter)
                print(r_answer)
                print(question_counter, "check")
                quest(question_counter)
                bot.send_message(
                    message.chat.id, f"Карточка номер {question_counter}: {question}"
                )
                bot.send_message(message.chat.id, "Ваш ответ: ")
                check_stage = 2

            elif check_stage == 2:
                update()
                answ(question_counter)
                print(r_answer)
                answer = message.text
                if answer == r_answer:
                    bot.send_message(message.chat.id, "Правильно")
                    correct += 1
                else:
                    bot.send_message(message.chat.id, "Неправильно")
                    bot.send_message(message.chat.id, f"Правильный ответ: {r_answer}")

                # update()

                if question_counter == col_of_q:
                    check_stage = 3
                else:
                    question_counter += 1
                    check_stage = 1

            elif check_stage == 3:
                correct_percentage = (correct / col_of_q) * 100
                bot.send_message(
                    message.chat.id,
                    f"Правильных ответов: {correct} из {col_of_q}, ({correct_percentage}%)",
                )
                stage = "null"
                with sq.connect("intervals.db") as con:
                    cur = con.cursor()
                    cur.execute(
                        "SELECT value FROM intervals WHERE user_id = ? AND set_name = ?",
                        (user_id, current_set[0]),
                    )
                    reminder_active = cur.fetchone()

                if reminder_active[0] == 1:
                    start_reminder_thread(
                        message.chat.id, correct_percentage, current_set
                    )
                    interval_minutes = calculate_next_interval(correct_percentage)
                    # bot.send_message(message.chat.id, f"Следующие напоминание через {interval_minutes//60} часов")

                menu(message)

            else:
                bot.send_message(
                    message.chat.id, "Ой ой произошла ошибка начни заного /strat"
                )

    elif stage == "add1":

        question_for_add = str(message.text)
        bot.send_message(message.chat.id, "Ответ: ")
        stage = "add2"

    elif stage == "add2":
        answer_for_add = str(message.text)
        add(question_for_add, answer_for_add)
        bot.send_message(message.chat.id, "Карточка успешно добавлена!")
        # update()
        # menu(message)
        # callback_data = "edit"
        stage = "null"

        edit_menu(message)

    elif stage == "del":
        number_question_for_del = message.text

        with sq.connect("cards.db") as con:
            cur = con.cursor()
            cur.execute(
                f"SELECT number FROM cards WHERE number = ? AND user_id = ?",
                (number_question_for_del, user_id),
            )
            cur.execute(
                f"DELETE FROM cards WHERE number = ? AND user_id = ?",
                (number_question_for_del, user_id),
            )
        stage = "null"
        update()
        bot.send_message(message.chat.id, "Карточка успешно удалена!")
        edit_menu(message)

    elif stage == "null":
        bot.send_message(message.chat.id, "Напишите /start чтобы начать")

    else:
        bot.send_message(
            message.chat.id,
            "Что-то пошло не так , попробуй перезапустить бота - /start",
        )


@bot.callback_query_handler(func=lambda callback: callback.data)
def chek_callback_data(callback):
    global stage
    global my_message
    global question
    global correct
    global question_counter
    global r_answer
    global check_stage
    global sets
    global user_id
    global text
    global col_of_q
    global current_set
    user_id = callback.from_user.id

    update_sets()

    if callback.data == "choose_set":
        bot.send_message(callback.message.chat.id, "Выберите набор:")
        update_sets()
        for i in range(1, col_of_set + 1):
            set_name = sets[i - 1][0]
            bot.send_message(callback.message.chat.id, f"{i} - {set_name}")
        stage = "choose"

    elif callback.data == "del_set":
        del_set_kb = types.InlineKeyboardMarkup()
        del_set_btn = types.InlineKeyboardButton(
            text="Выход", callback_data="exit_to_set_menu"
        )
        del_set_kb.add(del_set_btn)
        bot.send_message(
            callback.message.chat.id,
            "Введите номер набора который хотите удалить или выйдете в меню",
            reply_markup=del_set_kb,
        )
        for i in range(0, len(sets)):
            text = f"{i+1} - {str(sets[i])[2:-3]}"
            bot.send_message(callback.message.chat.id, text)
        stage = "del_set"

    elif callback.data == "add_set":
        exit_kb = types.InlineKeyboardMarkup()
        btn1 = types.InlineKeyboardButton(text="Выход", callback_data="exit_to_main")
        exit_kb.add(btn1)
        bot.send_message(
            callback.message.chat.id,
            "Введите название набора или выйдете в меню",
            reply_markup=exit_kb,
        )
        stage = "add_set"

    elif current_set not in sets:
        choose_set_kb = types.InlineKeyboardMarkup()
        choose_set_btn = types.InlineKeyboardButton(
            text="Выбрать набор", callback_data="choose_set"
        )
        choose_set_kb.add(choose_set_btn)
        bot.send_message(
            callback.message.chat.id,
            "Пожалуйста выберите набор",
            reply_markup=choose_set_kb,
        )

    else:
        if callback.data == "exit_to_main":
            start(callback.message)

        elif callback.data == "exit_to_set_menu":
            set_menu(callback.message)

        elif callback.data == "finish_editing":
            update()
            print(col_of_q)
            if col_of_q <= 1:
                low_exit_kb = types.InlineKeyboardMarkup()
                lbtn1 = types.InlineKeyboardButton(
                    text="Выйти в меню", callback_data="exit_to_cards_menu"
                )
                lbtn2 = types.InlineKeyboardButton(
                    text="Вернуться к редактированию", callback_data="edit"
                )
                low_exit_kb.add(lbtn1)
                low_exit_kb.add(lbtn2)
                bot.send_message(
                    callback.message.chat.id,
                    "Вы завершили редактирование но у вас слишком мало (минимум 2) вы можете выйти в меню или вернуться к редактированию",
                    reply_markup=low_exit_kb,
                )
            else:
                with sq.connect("intervals.db") as con:
                    cur = con.cursor()
                    cur.execute(
                        f"SELECT value FROM intervals WHERE user_id = ? AND set_name = ?",
                        (user_id, current_set[0]),
                    )
                    reminder_active = cur.fetchone()

                if reminder_active[0] == 1:
                    menu(callback.message)
                else:
                    repeat_kb = types.InlineKeyboardMarkup()
                    btn1 = types.InlineKeyboardButton(
                        text="Выйти в меню", callback_data="exit_to_cards_menu"
                    )
                    btn2 = types.InlineKeyboardButton(
                        text="Начать отсчёт", callback_data="time_start"
                    )
                    repeat_kb.add(btn1)
                    repeat_kb.add(btn2)
                    bot.send_message(
                        callback.message.chat.id,
                        "Похоже вы завершили редактирование, для более эффективного запоминания информации вы можете начать отсчёт времени и бот будет сообщать вам когда стоит проверить знания или вы просто хотите выйти в меню?",
                        reply_markup=repeat_kb,
                    )

        elif callback.data == "exit_to_cards_menu":
            menu(callback.message)

        elif callback.data == "time_start":
            # global current_set

            set_intervals_on(current_set, user_id, callback.message)

            bot.send_message(
                callback.message.chat.id,
                "Отлично! Для начала напоминаний пройдите тестирование в этом наборе чтобы определить интервал повторения",
            )
            menu(callback.message)

        elif callback.data == "check_from_reminder":
            global reminder_set
            current_set = reminder_set
            update()
            if col_of_q <= 1:
                bot.send_message(
                    callback.message.chat.id,
                    "Добавте карточек в набор, их слишком мало (минимум 2)",
                )
                menu(callback.message)
            else:
                bot.send_message(callback.message.chat.id, "Вы решили проверить знания")
                quest(1)
                bot.send_message(
                    callback.message.chat.id, f"Карточка номер 1: {question}"
                )
                bot.send_message(callback.message.chat.id, "Ваш ответ: ")
                answ(1)
                print(r_answer)
                update()
                correct = 0
                question_counter = 1
                check_stage = 2
                stage = "check"

        elif callback.data == "check":
            update()
            if col_of_q <= 1:
                bot.send_message(
                    callback.message.chat.id,
                    "Добавте карточек в набор, их слишком мало (минимум 2)",
                )
                menu(callback.message)
            else:
                bot.send_message(callback.message.chat.id, "Вы решили проверить знания")
                quest(1)
                bot.send_message(
                    callback.message.chat.id, f"Карточка номер 1: {question}"
                )
                bot.send_message(callback.message.chat.id, "Ваш ответ: ")
                answ(1)
                print(r_answer)
                update()
                correct = 0
                question_counter = 1
                check_stage = 2
                stage = "check"

        elif callback.data == "edit":
            edit_menu = types.InlineKeyboardMarkup()
            btn1 = types.InlineKeyboardButton(
                text="Добавить карточки", callback_data="add"
            )
            btn2 = types.InlineKeyboardButton(
                text="Удалить карточки", callback_data="delite"
            )
            btn3 = types.InlineKeyboardButton(
                text="Выход", callback_data="finish_editing"
            )
            edit_menu.add(btn1)
            edit_menu.add(btn2)
            edit_menu.add(btn3)
            bot.send_message(
                chat_id=callback.message.chat.id,
                text="Выберите что вы будите делать: ",
                reply_markup=edit_menu,
            )

        elif callback.data == "add":
            bot.send_message(callback.message.chat.id, "Вы решили добавить карточки")
            # update()
            bot.send_message(callback.message.chat.id, "Вопрос:")
            stage = "add1"

        elif callback.data == "delite":
            bot.send_message(callback.message.chat.id, "Вы решили удалить карточки")
            update()
            text = ""
            print(col_of_q, "col_of_q")
            for i in range(1, col_of_q + 1):
                quest(i)
                answ(i)
                text += f"{i} - {question} / {r_answer}\n"
            bot.send_message(callback.message.chat.id, text)

            bot.send_message(
                callback.message.chat.id, "Номер карточки которую хотите удалить: "
            )
            stage = "del"


try:
    bot.polling()
except KeyboardInterrupt:
    print("Exit")
