import configparser
import sys
import os
import urllib.request
import ssl


def validate_config(config):
    REQUIRED_PARAMS = {
        'package_name': str,
        'repository': str,
        'mode': str,
        'output_file': str,
        'max_depth': int,
        'filter_substring': str
    }
    
    #Допустимые значения для mode 
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
        
        # Валидация для mode
        if validated_params['mode'].lower() not in VALID_MODES:
            raise ValueError(f"Недопустимое значение для mode. Допустимые значения: {', '.join(VALID_MODES)}")
        
        # Валидация для имени файла
        if not validated_params['output_file'].lower().endswith(('.png', '.jpg', '.jpeg', '.svg')):
            raise ValueError("output_file должен иметь расширение изображения (.png, .jpg, .jpeg, .svg)")
        
        return validated_params
    
    except Exception as e:
        print(f"Ошибка в конфигурации: {str(e)}", file=sys.stderr)
        sys.exit(1)

def fetch_cargo_toml_remote(url):
    """Загружает Cargo.toml из удаленного репозитория"""
    try:
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(url, context=context, timeout=10) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        raise RuntimeError(f"Ошибка загрузки Cargo.toml: {str(e)}")

def fetch_cargo_toml_local(path):
    # for local
    try:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Файл не найден: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise RuntimeError(f"Ошибка чтения локального файла: {str(e)}")

def parse_dependencies(content):
    # dependencies from toml
    dependencies = []
    in_dependencies_section = False
    
    for line in content.splitlines():
        line = line.strip()
        
        # Определение секции зависимостей
        if line.startswith('['):
            in_dependencies_section = line == '[dependencies]'
            continue
        
        # Пропуск комментариев и пустых строк
        if not line or line.startswith('#') or not in_dependencies_section:
            continue
        
        # Извлечение имени пакета (до первого '=')
        if '=' in line:
            dep_name = line.split('=', 1)[0].strip()
            # Проверка на вложенные секции (например, [dependencies.subpkg])
            if '.' not in dep_name and not dep_name.startswith('['):
                dependencies.append(dep_name)
    
    return dependencies

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
    
    # Вывод
    print("Настройки приложения:")
    for key, value in params.items():
        print(f"{key}: {value}")

    # Этап 2: Сбор данных о зависимостях
    try:
        # Определение источника Cargo.toml
        if params['mode'] == 'remote':
            cargo_content = fetch_cargo_toml_remote(params['repository'])
        else:  # local
            cargo_content = fetch_cargo_toml_local(params['repository'])
        
        # Извлечение зависимостей
        dependencies = parse_dependencies(cargo_content)
        
        # Вывод результатов (требование этапа 2)
        print(f"\nПрямые зависимости пакета {params['package_name']}:")
        if dependencies:
            for dep in dependencies:
                print(f"- {dep}")
        else:
            print("Зависимости не найдены")
    
    except Exception as e:
        print(f"Ошибка получения зависимостей: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()