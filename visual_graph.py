import configparser
import sys
import os

def validate_config(config):
    """Проверяет корректность параметров конфигурации"""
    # Обязательные параметры и их типы
    REQUIRED_PARAMS = {
        'package_name': str,
        'repository': str,
        'mode': str,
        'output_file': str,
        'max_depth': int,
        'filter_substring': str
    }
    
    # Допустимые значения для режима
    VALID_MODES = ['local', 'remote']
    
    try:
        # Проверка наличия секции
        if 'settings' not in config:
            raise ValueError("Отсутствует секция [settings] в конфигурационном файле")
        
        settings = config['settings']
        validated_params = {}
        
        # Валидация каждого параметра
        for param, param_type in REQUIRED_PARAMS.items():
            if param not in settings:
                raise ValueError(f"Отсутствует обязательный параметр: {param}")
            
            value = settings[param].strip()
            
            if param_type == int:
                try:
                    int_value = int(value)
                    if int_value < 0:
                        raise ValueError(f"Параметр {param} должен быть неотрицательным")
                    validated_params[param] = int_value
                except ValueError:
                    raise ValueError(f"Параметр {param} должен быть целым числом")
            else:
                if not value:
                    raise ValueError(f"Параметр {param} не может быть пустым")
                validated_params[param] = value
        
        # Специальная валидация для режима
        if validated_params['mode'].lower() not in VALID_MODES:
            raise ValueError(f"Недопустимое значение для mode. Допустимые значения: {', '.join(VALID_MODES)}")
        
        # Валидация имени файла (простая проверка расширения)
        if not validated_params['output_file'].lower().endswith(('.png', '.jpg', '.jpeg', '.svg')):
            raise ValueError("output_file должен иметь расширение изображения (.png, .jpg, .jpeg, .svg)")
        
        return validated_params
    
    except Exception as e:
        print(f"Ошибка в конфигурации: {str(e)}", file=sys.stderr)
        sys.exit(1)

def main():
    config = configparser.ConfigParser()
    
    # Чтение конфигурационного файла
    try:
        if not os.path.exists('config.ini'):
            raise FileNotFoundError("Файл config.ini не найден в текущей директории")
        
        config.read('config.ini', encoding='utf-8')
    except Exception as e:
        print(f"Ошибка чтения конфигурации: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    # Валидация параметров
    params = validate_config(config)
    
    # Вывод параметров в формате ключ-значение
    print("Настройки приложения:")
    for key, value in params.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    main()