import pytest
from unittest.mock import AsyncMock
from aiohttp import ClientSession
from your_module import logs


@pytest.mark.asyncio
async def test_logs(mocker):
    # Создаем mock-объект для содержимого ответа
    mock_response = mocker.Mock()
    mock_response.content.__aiter__.return_value = iter(
        [b'log line 1\n', b'log line 2\n'])

    # Создаем асинхронный mock-объект для сессии
    mock_session = AsyncMock(spec=ClientSession)
    # Настраиваем поведение этого объекта при вызове get
    mock_session.get.return_value.__aenter__.return_value = mock_response

    # Создаем mock-объект для UnixConnector
    mock_connector = mocker.Mock()
    # Подменяем настоящий UnixConnector на наш mock-объект
    mocker.patch('aiohttp.UnixConnector', return_value=mock_connector)

    # Подменяем настоящий ClientSession на наш mock-объект
    mocker.patch('aiohttp.ClientSession', return_value=mock_session)

    # Подменяем настоящую функцию print на mock, чтобы мы могли отследить ее вызовы
    mock_print = mocker.patch('builtins.print')

    # Вызываем тестируемую функцию
    await logs('container1', 'test')

    # Проверяем, что был сделан запрос с правильными аргументами
    mock_session.get.assert_called_once_with(
        "http://xx/containers/container1/logs?follow=1&stdout=1"
    )

    # Проверяем, что функция print была вызвана с правильными аргументами
    mock_print.assert_any_call('test', b'log line 1\n')
    mock_print.assert_any_call('test', b'log line 2\n')
