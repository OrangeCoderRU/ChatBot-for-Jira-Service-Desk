import telebot
import sqlite3
from jira import JIRA

login = "your_jira_login"
api_key = "account_api_key"

jira_options = {'server': 'https://project-dip.atlassian.net'} # your jira project url

def jira_login():
    try:
        jira = JIRA(options=jira_options, basic_auth=(login, api_key))
        return jira
    except:
        return "Error login"

jira = jira_login()

def sql_connection():
    """Подключение/создание файла БД"""
    con = sqlite3.connect("knowledge_base.db")
    return con

def sql_out(con):
    """Выборка из БД"""
    cursor = con.cursor()
    cursor.execute("""SELECT * FROM knowledge_base""")
    rows = cursor.fetchall()
    return rows

con = sql_connection()
result = sql_out(con)

def telegram_login():
    try:
        bot = telebot.TeleBot('1225159920:AAGzshVNwc52UEX12AfrTkhlLNf6IjjcKeY')
        return bot
    except:
        return "Telegram Error"

if telegram_login() != "Telegram Error":
    bot = telegram_login()
else:
    print("Telegram не отвечает...")

keyboard_start = telebot.types.ReplyKeyboardMarkup(True)
keyboard_start.row('Хочу задать вопрос', 'Нет, сейчас ничего')
hideBoard = telebot.types.ReplyKeyboardRemove()

keyboard_yes_no = telebot.types.ReplyKeyboardMarkup(True)
keyboard_yes_no.row('Да, помогло', 'Нет, не помогло')

@bot.message_handler(commands=['start'])
def start_message(message):
    if jira != "Error login":
        bot.send_message(message.chat.id,'Привет, ты запустил бота техподдержки с интеграцией Jira.'+
        '\nУ вас имеется какая-то проблема?',
        reply_markup=keyboard_start)
    else:
        bot.send_message(message.chat.id, 'К сожалению сервера  Jira недоступны, попробуйте позже')

@bot.message_handler(content_types=['text'])
def problem(message):
    if message.text == "Хочу задать вопрос":
        bot.send_message(message.chat.id, "Опишите, что у вас случилось?", reply_markup=hideBoard)
        bot.register_next_step_handler(message, problem_read)
    elif message.text == "Нет, сейчас ничего":
        bot.send_message(message.chat.id, "Хорошо, как только возникнут трудности, обращайтесь!", reply_markup=keyboard_start)

def problem_read(message):
    bot.send_message(message.chat.id, "Вы задали вопрос - " + message.text)
    global problem_summary

    problem_summary = message.text

    # Алгоритм поиска возможного решения
    list_res = [] # результаты поиска
    # приведение запроса в нижний регистр и перевод в массив
    problem_list = problem_summary.lower().split()
    bool_search = False # статус соответствия статьи

    for el in result: # итерирование выборки из базы знаний
        for prob in problem_list: # итерирование по словам поискового запроса
            if prob in list(el)[0]:
                bool_search = True
            else:
                bool_search = False
        if bool_search: # если статья подошла, добавить в результирующий массив статью
                list_res.append(list(el))


    if len(list_res) > 0:
        bot.send_message(message.chat.id, "Вот что удалось найти:")
        i = 1
        for answ in list_res:
            bot.send_message(message.chat.id, str(i) + ") " + answ[0] + "\n" + " " + "\n"+ answ[1])
            i+=1
        bot.send_message(message.chat.id, "Возможные варианты решения помогли?", reply_markup=keyboard_yes_no)
        bot.register_next_step_handler(message, ticket_ques)
    else:
        bot.send_message(message.chat.id, "К сожалению поиск не дал результатов(")
        bot.send_message(message.chat.id, "Тогда инициируем заявку в Jira Service Desk\n" + " \n" +
        "Изложите более подробное описание проблемы для заявки:", reply_markup=hideBoard)
        bot.register_next_step_handler(message, create_ticket)

def ticket_ques(message):
    if message.text == "Да, помогло":
        jira.create_issue(fields={
            'project': {'key': 'YYOU'},
            'issuetype': {
                "name": "Service Request"
            },
             'summary': problem_summary + " (Решено автоматически)",
             'description': "",
        })

        last_issue = jira.search_issues("project=YYOU")[0].key
        issue = jira.issue(last_issue)
        transitions = jira.transitions(issue)
        # 851 Ответить клиенту
        # 891 В работе
        # 921 Передать на рассмотрение
        # 761 Решить эту проблему
        # 901 Отменить запрос
        # 871 В ожидании


        # Производим переход статуса заявки:
        jira.transition_issue(issue, transition="761")

        bot.send_message(message.chat.id, "Отлично!\nесли что, обращайтесь снова", reply_markup=keyboard_start)
    elif message.text =="Нет, не помогло":
        bot.send_message(message.chat.id, "Инициируем заявку в Jira Service Desk\n" + " \n" +
        "Изложите более подробное описание проблемы для заявки:", reply_markup=hideBoard)

        bot.register_next_step_handler(message, create_ticket)

def create_ticket(message):
    global problem_descryprtion
    problem_descryprtion = message.text
    bot.send_message(message.chat.id, "Окей, заявка создается")
    # name = "randomsabm@gmail.com"
    jira.create_issue(fields={
        'project': {'key': 'YYOU'},
        'issuetype': {
            "name": "Service Request"
        },
         'summary': problem_summary,
         'description': problem_descryprtion,
         # 'reporter': {'name': name}, # if need repoter 
    })

    last_issue = jira.search_issues("project=YYOU")[0].key
    bot.send_message(message.chat.id, "Готово! Заявка зарегистрированна с ключом: " +  last_issue, reply_markup=keyboard_start)

print("Бот запущен...")

bot.polling(none_stop=True, interval=0)
