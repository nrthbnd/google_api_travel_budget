import argparse

from services import DRIVE_SERVICE, EMAIL_USER, SHEETS_SERVICE


def get_list_obj(service):
    """Функция чтения списка документов с таблицами."""
    response = service.files().list(
        q='mimeType="application/vnd.google-apps.spreadsheet"').execute()
    return response['files']


def clear_disk(service):
    """Функция удаления всех документов с таблицами."""
    for spreadsheet in get_list_obj(service):
        response = service.files().delete(fileId=spreadsheet['id'])
        response.execute()
    return 'Документы удалены'


def set_user_permissions(service, spreadsheetId):
    """Выдаём права личному гугл-аккаунту на доступ к документу."""
    permissions_body = {'type': 'user',
                        'role': 'writer',
                        'emailAddress': EMAIL_USER}
    service.permissions().create(
        fileId=spreadsheetId,
        body=permissions_body,
        fields='id'
    ).execute()


def create_spreadsheet(service, data):
    """Создаём документ с таблицами."""
    # Тут будет распаковываться значение аргумента, которое состоит
    # из двух частей, записанных через запятую: название документа, сумма
    title, cash = data.split(',')
    spreadsheet_body = {
        'properties': {
            'title': title.strip(),
            'locale': 'ru_RU'
        },
        'sheets': [{
            'properties': {
                'sheetType': 'GRID',
                'sheetId': 0,
                'title': 'Отпуск',
                'gridProperties': {
                    'rowCount': 100,
                    'columnCount': 100
                }
            }
        }]
    }
    request = service.spreadsheets().create(body=spreadsheet_body)
    response = request.execute()
    spreadsheetId = response['spreadsheetId']
    # Вызываем функцию выдачи прав
    set_user_permissions(DRIVE_SERVICE, spreadsheetId)
    spreadsheet_update_values(
        SHEETS_SERVICE,
        spreadsheetId,
        cash,
        default=True,
    )
    print(f'https://docs.google.com/spreadsheets/d/{spreadsheetId}')
    return f'Был создан документ с ID {spreadsheetId}'


def read_values(service, spreadsheetId):
    """Построчно возвращать считанные данные в виде списка списков."""
    range = "A1:E30"
    response = service.spreadsheets().values().get(
        spreadsheetId=spreadsheetId,
        range=range,
    ).execute()
    return response['values']


def spreadsheet_update_values(service, spreadsheetId, data, default=False):
    """Обновление данных в документе с таблицами."""
    if default:
        table_values = [
            ['Бюджет путешествия'],
            ['Весь бюджет', data],
            ['Все расходы', '=SUM(E7:E30)'],
            ['Остаток', '=B2-B3'],
            ['Расходы'],
            ['Описание', 'Тип', 'Кол-во', 'Цена', 'Стоимость'],
        ]
    else:
        # Получаем данные, которые уже есть в таблице, функцию read_values
        # напишем следующей.
        table_values = read_values(service, spreadsheetId)
        # Дополняем список новой строкой, которая передаётся через аргумент.
        # Строка должна быть переведена в список, а элементы — очищены от пробелов
        table_values.append(list(map(str.strip, data.split(','))))
    # Формируем тело запроса.
    request_body = {
        'majorDimension': 'ROWS',
        'values': table_values
    }
    # Формируем запрос.
    request = service.spreadsheets().values().update(
        spreadsheetId=spreadsheetId,
        range="A1:E30",
        valueInputOption="USER_ENTERED",
        body=request_body
    )
    # Выполняем запрос.
    request.execute()
    return 'Документ обновлён'


def main(args):
    # Аргумент для функции, которая выводит список
    # всех документов с таблицами
    if args.list:
        return get_list_obj(DRIVE_SERVICE)
    # Аргумент для функции, которая удаляет
    # все документы с таблицами
    if args.clear_all:
        return clear_disk(DRIVE_SERVICE)
    if args.create is not None:
        return create_spreadsheet(
            SHEETS_SERVICE,
            args.create
        )

    spreadsheet_id = None
    if args.id is not None:
        spreadsheet_id = args.id
    else:
        # Получаем список всех таблиц
        spreadsheets = get_list_obj(DRIVE_SERVICE)
        if spreadsheets:
            spreadsheet_id = spreadsheets[0]['id']

    if args.update is not None:
        return spreadsheet_update_values(
            SHEETS_SERVICE,
            spreadsheet_id,
            args.update
        )


if __name__ == '__main__':
    # Экземпляра класса ArgumentParser
    parser = argparse.ArgumentParser(description='Бюджет путешествий')
    # Аргументы командной строки
    parser.add_argument(
        '-c',
        '--create',
        help='Создать файл - введите "имя, бюджет"',
    )
    parser.add_argument(
        '-cl',
        '--clear_all',
        action='store_true',
        help='Удалить все spreadsheets',
    )
    parser.add_argument(
        '-i',
        '--id',
        help='Указать id spreadsheet',
    )
    parser.add_argument(
        '-ls',
        '--list',
        action='store_true',
        help='Вывести все spreadsheets',
    )
    parser.add_argument(
        '-u',
        '--update',
        help='Обновить данные таблицы',
    )
    # Парсинг аргументов командной строки
    args = parser.parse_args()

    print(main(args))
