import re
from typing import Union, List

import sqlalchemy.orm
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import ContentTypes

from app import dp, config
from app.db.models import User, Item
from app.dialogue import StateItem, States
from app.dialogue import keyboard_remove
from app.dialogue.filters import filter_su, filter_admin, filter_user_inactive
from app.messages import MESSAGES
from app.middlewares import trace, add_middlewares, sql_result


# inactive
@dp.message_handler(filter_user_inactive,
                    state='*')
@add_middlewares(mixed_handler='message',
                 use_resolve_state=True,
                 use_trace=True)
async def inactive(user_id,
                   context,
                   message: types.Message) -> Union[StateItem, None]:
    await message.reply(MESSAGES['user_inactive'], reply=False)
    return States.STATE_1_MAIN


# /admin
@dp.message_handler(filter_su,
                    commands=['admin'],
                    state='*')
@add_middlewares(mixed_handler='message',
                 use_trace=True)
async def admin(user_id,
                context,
                message: types.Message):
    if not filter_admin(message):
        config.app.admin.append(user_id)
        await message.reply(MESSAGES['admin_enable'], reply=False)
    else:
        config.app.admin.remove(user_id)
        await message.reply(MESSAGES['admin_disable'], reply=False)


# /clear
@dp.message_handler(filter_su,
                    commands=['clear'],
                    state='*')
@add_middlewares(mixed_handler='message',
                 use_resolve_state=True,
                 use_trace=True)
async def clear_state(user_id,
                      context,
                      message: types.Message) -> Union[StateItem, None]:
    return States.STATE_1_MAIN


# /start
@dp.message_handler(commands=['start'],
                    state='*')
@add_middlewares(mixed_handler='message',
                 use_resolve_state=True,
                 use_db_session=True,
                 use_trace=True)
async def start(user_id,
                context,
                message: types.Message,
                session: sqlalchemy.orm.Session) -> Union[StateItem, None]:
    rowcount, user, _ = sql_result(session.query(User)
                                   .filter(User.uid == user_id))
    if rowcount == 0:
        trace(User)(uid=user_id,
                    username=message.from_user.username) \
            .insert_me(session)
        reply_text = MESSAGES['greetings']
        next_state = States.STATE_0_REQUEST_CITY
    else:
        reply_text = MESSAGES['yo']
        next_state = States.STATE_1_MAIN
    await message.reply(reply_text, reply=False)

    return next_state


# get geo
@dp.message_handler(state=States.STATE_0_REQUEST_CITY,
                    content_types=ContentTypes.TEXT)
@add_middlewares(mixed_handler='message',
                 use_resolve_state=True,
                 use_db_session=True,
                 use_trace=True)
async def location(user_id,
                   context,
                   message: types.Message,
                   session: sqlalchemy.orm.Session) -> Union[StateItem, None]:
    rowcount, user, _ = sql_result(session.query(User)
                                   .filter(User.uid == user_id),
                                   raise_on_empty_result=True)
    user.location = message.text
    await message.reply(MESSAGES['sign_up_complete'],
                        reply=False,
                        reply_markup=keyboard_remove)
    next_state = States.STATE_1_MAIN
    return next_state


# /cancel
@dp.message_handler(commands=['cancel'],
                    state=[States.STATE_2_UPLOAD, States.STATE_3_DELETE, States.STATE_4_SEARCH])
@add_middlewares(mixed_handler='message',
                 use_resolve_state=True,
                 use_trace=True)
async def cancel(user_id,
                 context,
                 message: types.Message) -> Union[StateItem, None]:
    await message.reply(MESSAGES['cancel'])
    return None


# /upload
@dp.message_handler(commands=['upload'],
                    state=States.STATE_1_MAIN)
@add_middlewares(mixed_handler='message',
                 use_resolve_state=True,
                 use_db_session=True,
                 use_trace=True)
async def upload_command(user_id,
                         context,
                         message: types.Message,
                         session: sqlalchemy.orm.Session) -> Union[StateItem, None]:
    _, user, _ = sql_result(session.query(User)
                            .filter(User.uid == user_id),
                            raise_on_empty_result=True)
    await message.reply(MESSAGES['upload'])
    return States.STATE_2_UPLOAD


def parse_upload(raw_text: str,
                 row_delimiter='\n',
                 column_delimiter=',',
                 trim_carriage_return=True) -> Union[List, None]:
    result = []
    if trim_carriage_return:
        raw_text = raw_text.replace('\r', '')
    rows = raw_text.split(row_delimiter)
    for item in [row.split(column_delimiter) for row in rows]:
        if len(item) != 2:
            result = None
            break
        else:
            result.append({'name': item[0], 'price': item[1]})
    return result


# process /upload
@dp.message_handler(state=States.STATE_2_UPLOAD)
@add_middlewares(mixed_handler='message',
                 use_resolve_state=True,
                 use_db_session=True,
                 use_trace=True)
async def upload_action(user_id,
                        context,
                        message: types.Message,
                        session: sqlalchemy.orm.Session) -> Union[StateItem, None]:
    _, user, _ = sql_result(session.query(User)
                            .filter(User.uid == user_id),
                            raise_on_empty_result=True)
    items_list = parse_upload(message.text)
    if items_list is None:
        await message.reply(MESSAGES['upload_parse_failed'])
        return States.STATE_2_UPLOAD
    rowcount, _, _ = sql_result(session.query(Item)
                                .filter(Item.owner_id == user.id)
                                .filter(Item.status < 9))
    if len(items_list) + rowcount > user.limit:
        await message.reply(MESSAGES['upload_limit_exceeded'].format(user.limit, message.text))
        return States.STATE_1_MAIN
    for item in items_list:
        Item(user.id, item['name'], item['price']) \
            .insert_me(session)
    await message.reply(MESSAGES['upload_complete'])
    return States.STATE_1_MAIN


# /delete
@dp.message_handler(commands=['delete'],
                    state=States.STATE_1_MAIN)
@add_middlewares(mixed_handler='message',
                 use_resolve_state=True,
                 use_db_session=True,
                 use_trace=True)
async def delete_action(user_id,
                        context: FSMContext,
                        message: types.Message,
                        session: sqlalchemy.orm.Session) -> Union[StateItem, None]:
    # save del_ids and request confirmation
    args: str = message.get_args()
    del_ids = re.sub('[ ,]+', ',', args)
    context_data = await context.get_data()
    context_data['delete_ids'] = del_ids
    await context.set_data(context_data)
    return States.STATE_3_DELETE


# confirm delete
@dp.message_handler(state=States.STATE_3_DELETE)
@add_middlewares(mixed_handler='message',
                 use_resolve_state=True,
                 use_db_session=True,
                 use_trace=True)
async def delete_action_confirmed(user_id,
                                  context: FSMContext,
                                  message: types.Message,
                                  session: sqlalchemy.orm.Session) -> Union[StateItem, None]:
    args: str = message.get_args()
    delete_confirmed = args.strip().lower() == 'да'
    context_data = await context.get_data()
    del_ids = context_data.get('delete_ids', None)
    reply_text = ''
    if del_ids == 'all':
        _, user, _ = sql_result(session.query(User)
                                .filter(User.uid == user_id))
        del_records = user.owner_items
    else:
        _, _, del_records = sql_result(session.query(Item)
                                       .join(User)
                                       .filter(User.uid == user_id)
                                       .filter(Item.id.in_(del_ids.split(','))))
    if delete_confirmed:
        # process delete
        for record in del_records:
            reply_text += f'{record!r} deleted\n'
            session.delete(record)
        return States.STATE_1_MAIN


# /search
@dp.message_handler(state=States.STATE_4_SEARCH)
@add_middlewares(mixed_handler='message',
                 use_resolve_state=True,
                 use_db_session=True,
                 use_trace=True)
async def search_action(user_id,
                        context,
                        message: types.Message,
                        session: sqlalchemy.orm.Session) -> Union[StateItem, None]:
    return States.STATE_1_MAIN


# /mycards
@dp.message_handler(commands=['mycards'],
                    state=States.STATE_1_MAIN)
@add_middlewares(mixed_handler='message',
                 use_db_session=True,
                 use_trace=True)
async def mycards(user_id,
                  context,
                  message: types.Message,
                  session: sqlalchemy.orm.Session):
    args = message.get_args()

    _, _, rows = sql_result(session.query(Item)
                            .join(User)
                            .filter(User.uid == user_id)
                            .filter(Item.status < 9))

    reply_text = Item.list_repr(rows)
    await message.reply(reply_text,
                        reply=False)
