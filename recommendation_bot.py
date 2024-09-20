from typing import Dict, Any

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery
import config
from dataclasses import dataclass, asdict, field
import json
import random
import texts as t
from aiogram.enums import ParseMode
from aiogram.types import LinkPreviewOptions

# Создаем объект бота
bot = Bot(token=config.token)
# Создаем диспетчер
dp = Dispatcher()


def generate_random_sequence(n: int):
    sequence = list(range(1, n + 1))
    random.shuffle(sequence)
    return sequence


@dataclass
class Questions:
    question: str
    answers_amount: int
    answers: dict

    def to_dict(self):
        return {'question': self.question, 'answers_amount': self.answers_amount, "answers": self.answers}


def loading_questions(file_path=config.quest_path):
    # Открытие файла для чтения
    with open(file_path, 'r', encoding='utf-8') as file:
        # Чтение содержимого файла
        data = file.read()
    # Преобразование содержимого файла в объект Python
    question_dict = json.loads(data)
    quest_list = []
    for i in question_dict:
        q = i['question']
        amount = i['answers_amount']
        answers = i['answers']
        quest_list.append(Questions(q, amount, answers))

    return quest_list


quest_list = loading_questions()


@dataclass
class Person:
    id: int
    username: str
    first_name: str
    last_name: str
    question_sequence: list = field(default_factory=dict)
    status: str = 'before_begin'
    status_times: dict = field(default_factory=dict)
    scores: dict = field(default_factory=dict)

    def to_dict(self):
        return {'id': self.id, 'username': self.username, "first_name": self.first_name, 'last_name': self.last_name,
                'question_sequence': self.question_sequence, 'status': self.status, 'status_times': self.status_times,
                'scores': self.scores}

    def __post_init__(self):
        self.question_sequence = generate_random_sequence(10)
        self.status_times = {'before_begin': [], 'in_progress': [], 'after_guest': []}
        self.scores = {'цифра': 0, 'метод': 0, 'психпед': 0, 'комму': 0, 'юри': 0}

def loading_persons(file_path=config.persons_path):
    # Открытие файла для чтения
    with open(file_path, 'r', encoding='utf-8') as file:
        # Чтение содержимого файла
        data = file.read()
    # Преобразование содержимого файла в объект Python
    persons_data = json.loads(data)
    persons_dict = {}
    for i in persons_data:
        id = i['id']
        username = i['username']
        first_name = i['first_name']
        last_name = i['last_name']
        question_sequence = i['question_sequence']
        status = i['status']
        status_times = i['status_times']
        scores = i['scores']
        persons_dict[id] = Person(id, username, first_name, last_name, question_sequence, status, status_times, scores)
    return persons_dict

persons_dict = loading_persons()

def save_person_list(person_list_to_save):
    #print(len(person_list_to_save))
    data = json.dumps([asdict(person_list_to_save[i]) for i in list(person_list_to_save.keys())], ensure_ascii=False,
                      default=str)

    with open('person_list.json', 'w', encoding='utf-8') as f:
        f.write(data)


async def print_recommendations(person: Person, message: Message):
    recommendation_text = t.recommendation_text
    await bot.send_message(message.chat.id, recommendation_text)



async def quiz(person: Person, quest_list_func: list, message: Message):
    if len(person.question_sequence) == 10:
        lets_start_text = t.lets_start_text
        await bot.send_message(message.chat.id, lets_start_text)
    if len(person.question_sequence) > 0:
        quest_num = person.question_sequence[0]
        q = quest_list_func[quest_num - 1]
        person.question_sequence.pop(0)
        j = q.answers_amount
        ans = list(q.answers.keys())
        #print(ans)
        num_indicator = 10 - len(person.question_sequence)
        text = 'Вопрос № ' + str(num_indicator) + '/10\n' + q.question + '\n\n' + 'ОТВЕТЫ\n'

        buttons = []
        for button in range(int(j)):
            title = str(button + 1)
            label = q.answers[ans[button]]['division'] + '_' + str(q.answers[ans[button]]['score'])
            text += (str(button + 1) + ' ' + ans[button] + '\n')
            buttons.append(InlineKeyboardButton(text=title, callback_data=label))
        inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
        await bot.send_message(message.chat.id, text, reply_markup=inline_keyboard)

    else:
        person.status = 'after_guest'
        person.status_times['after_guest'].append(message.date)
        save_person_list(persons_dict)
        await print_recommendations(persons_dict[message.chat.id], message)


@dp.callback_query()
async def callback_query_handler(callback_query: CallbackQuery):
    div, score = callback_query.data.split('_')
    persons_dict[callback_query.message.chat.id].scores[div] += int(score)
    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
    await quiz(persons_dict[callback_query.message.chat.id], quest_list, callback_query.message)


# Этот хэндлер будет срабатывать на команду "/start"  
@dp.message(CommandStart())
async def process_start_command(message: Message):
    if message.chat.id not in persons_dict.keys():
        await message.answer(t.greeting)

        persons_dict[message.chat.id] = Person(message.chat.id, message.chat.username, message.chat.first_name,
                                               message.chat.last_name)
        persons_dict[message.chat.id].status_times['before_begin'].append(message.date)
        persons_dict[message.chat.id].status = 'before_begin'
        save_person_list(persons_dict)
    elif 'in_progress' == persons_dict[message.chat.id].status:
        await message.answer(t.in_progress)
    else:
        await message.answer(t.greeting)
        save_person_list(persons_dict)


@dp.message(Command(commands='reset'))
async def process_reset_command(message: Message):
    if message.chat.id not in persons_dict.keys():
        await process_start_command(message)
    else:
        save_person_list(persons_dict)
        person = persons_dict[message.chat.id]
        person.question_sequence = generate_random_sequence(10)
        persons_dict[message.chat.id].status = 'before_begin'
        persons_dict[message.chat.id].status_times['before_begin'].append(message.date)
        person.scores = {'цифра': 0, 'метод': 0, 'психпед': 0, 'комму': 0, 'юри': 0}
        await message.answer(t.reset_text)


# Этот хэндлер будет срабатывать на команду "/help"
@dp.message(Command(commands='help'))
async def process_help_command(message: Message):
    if message.chat.id not in persons_dict.keys():
        await process_start_command(message)
    else:
        await message.answer(t.help)


@dp.message(Command(commands='begin'))
async def process_startquest_command(message: Message):
    if message.chat.id not in persons_dict.keys():
        await process_start_command(message)
    else:
        persons_dict[message.chat.id].status_times['in_progress'].append(message.date)
        persons_dict[message.chat.id].status = 'in_progress'
        await quiz(persons_dict[message.chat.id], quest_list, message)


# print(message.date, message.chat.id, message.chat.username, message.chat.first_name, message.chat.last_name)


@dp.message(Command(commands='zyfra'))
async def process_zyfra_command(message: Message):
    if message.chat.id not in persons_dict.keys():
        await process_start_command(message)
    else:
        person = persons_dict[message.chat.id]
        zyfra_text = t.zyfra_preamble
        if person.scores['цифра'] > 2:
            zyfra_text += t.zyfra_3
        elif person.scores['цифра'] > 1:
            zyfra_text += t.zyfra_2
        else:
            zyfra_text += t.zyfra_1
        no_preview = LinkPreviewOptions(is_disabled=True)
        await message.answer(zyfra_text, parse_mode=ParseMode.MARKDOWN, link_preview_options=no_preview)


@dp.message(Command(commands='method'))
async def process_method_command(message: Message):
    if message.chat.id not in persons_dict.keys():
        await process_start_command(message)
    else:
        person = persons_dict[message.chat.id]
        method_text = t.method_preamble
        if person.scores['метод'] > 2:
            method_text += t.method_3
        elif person.scores['метод'] > 1:
            method_text += t.method_2
        else:
            method_text += t.method_1
        no_preview = LinkPreviewOptions(is_disabled=True)
        await message.answer(method_text, parse_mode=ParseMode.MARKDOWN, link_preview_options=no_preview)


@dp.message(Command(commands='psy_ped'))
async def process_psy_ped_command(message: Message):
    if message.chat.id not in persons_dict.keys():
        await process_start_command(message)
    else:
        person = persons_dict[message.chat.id]
        psy_text = t.psy_ped_preamble
        if person.scores['психпед'] > 2:
            psy_text += t.psy_ped_3
        elif person.scores['психпед'] > 1:
            psy_text += t.psy_ped_2
        else:
            psy_text += t.psy_ped_1
        no_preview = LinkPreviewOptions(is_disabled=True)
        await message.answer(psy_text, parse_mode=ParseMode.MARKDOWN, link_preview_options=no_preview)


@dp.message(Command(commands='communication'))
async def process_communication_command(message: Message):
    if message.chat.id not in persons_dict.keys():
        await process_start_command(message)
    else:
        person = persons_dict[message.chat.id]
        comm_text = t.comm_preamble
        if person.scores['комму'] > 3:
            comm_text += t.comm_3
        elif person.scores['комму'] > 2:
            comm_text += t.comm_2
        else:
            comm_text += t.comm_1
        no_preview = LinkPreviewOptions(is_disabled=True)
        await message.answer(comm_text, parse_mode=ParseMode.MARKDOWN, link_preview_options=no_preview)


@dp.message(Command(commands='legal'))
async def process_legal_command(message: Message):
    if message.chat.id not in persons_dict.keys():
        await process_start_command(message)
    else:
        person = persons_dict[message.chat.id]
        yr_text = t.yr_preamble
        if person.scores['юри'] > 1:
            yr_text += t.yr_3
        elif person.scores['юри'] > 2:
            yr_text += t.yr_2
        else:
            yr_text += t.yr_1
        no_preview = LinkPreviewOptions(is_disabled=True)
        await message.answer(yr_text, parse_mode=ParseMode.MARKDOWN, link_preview_options=no_preview)


# Этот хэндлер будет срабатывать на отправку боту фото  
async def send_photo_echo(message: Message):
    await message.reply_photo(message.photo[0].file_id)


# Этот хэндлер будет срабатывать на любые ваши текстовые сообщения,  
# кроме команд "/start" и "/help"  
async def send_echo(message: Message):
    await message.reply(text=message.text)


# Запускаем бота
if __name__ == '__main__':
    dp.run_polling(bot)
