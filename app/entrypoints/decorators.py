from functools import wraps

# Словарь для хранения функций по action
ACTION_HANDLERS = {}

def action_handler(actions):
    """
    Декоратор для регистрации функции на определенные action.
    actions: список action, при которых функция будет вызвана
    """
    def decorator(func):
        for action in actions:
            if action not in ACTION_HANDLERS:
                ACTION_HANDLERS[action] = []
            ACTION_HANDLERS[action].append(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator
