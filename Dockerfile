FROM python:3.12

# Установка переменных окружения
ENV PYTHONUNBUFFERED 1

# Установка Poetry
RUN pip install poetry

# Создание рабочей директории
RUN mkdir /code
WORKDIR /code

# Копирование файлов проекта
COPY pyproject.toml /code/
COPY . /code/

# Установка зависимостей
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Запуск приложения
CMD ["poetry", "run", "python", "main.py"]