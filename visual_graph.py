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

def fetch_test_graph_local(path):
    """Читает текстовый файл с описанием графа"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise RuntimeError(f"Ошибка чтения текстового файла: {str(e)}")

##def parse_dependencies(content):
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

def parse_test_graph(content):
    """Корректный парсер тестового графа с обработкой комментариев"""
    graph = {}
    for line in content.splitlines():
        # Удаляем комментарии и лишние пробелы
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        
        # Разделяем узел и зависимости
        if ':' not in line:
            continue
            
        node, deps_part = line.split(':', 1)
        node = node.strip().upper()  # Требование: большие латинские буквы
        
        # Обрабатываем зависимости
        dependencies = []
        for dep in deps_part.split():
            dep_clean = dep.strip()
            if dep_clean and dep_clean.isupper() and dep_clean.isalpha():  # Только A-Z
                dependencies.append(dep_clean)
        
        graph[node] = dependencies
    
    return graph

def bfs_recursive(graph, start, max_depth, filter_substring):
    """Корректный рекурсивный BFS с учётом глубины и фильтрации"""
    visited = set()
    result = {}
    order = []  # Для сохранения порядка вывода
    
    def _bfs(nodes, current_depth):
        if current_depth > max_depth or not nodes:
            return
        
        next_level = []
        current_level_nodes = []
        
        for node in nodes:
            # Пропускаем уже посещённые и отфильтрованные
            if node in visited or (filter_substring and filter_substring in node):
                continue
            
            visited.add(node)
            current_level_nodes.append(node)
            
            # Получаем зависимости только если глубина позволяет
            dependencies = graph.get(node, []) if current_depth < max_depth else []
            filtered_deps = []
            
            for dep in dependencies:
                if dep in visited or (filter_substring and filter_substring in dep):
                    continue
                
                filtered_deps.append(dep)
                if dep not in next_level and dep not in visited:
                    next_level.append(dep)
            
            result[node] = filtered_deps
        
        # Сохраняем порядок обработки уровня
        order.extend(current_level_nodes)
        _bfs(next_level, current_depth + 1)
    
    _bfs([start], 0)
    
    # Формируем результат в правильном порядке
    ordered_result = {}
    for node in order:
        if node in result:
            ordered_result[node] = result[node]
    
    return ordered_result

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

    # Этап 3: Построение графа зависимостей
    try:
        if params['mode'] == 'remote':
            # Для удаленного режима получаем только прямые зависимости (как в этапе 2)
            cargo_content = fetch_cargo_toml_remote(params['repository'])
            dependencies = parse_dependencies(cargo_content)
            graph = {params['package_name']: dependencies}
        else:  # local - тестовый режим
            content = fetch_test_graph_local(params['repository'])
            graph = parse_test_graph(content)
        
        # Построение графа с BFS
        dependency_graph = bfs_recursive(
            graph=graph,
            start=params['package_name'],
            max_depth=params['max_depth'],
            filter_substring=params['filter_substring']
        )
        
        # Вывод результата (требование этапа 3)
        print(f"\nГраф зависимостей для {params['package_name']} (глубина ≤ {params['max_depth']}):")
        if dependency_graph:
            for node, deps in dependency_graph.items():
                print(f"{node} -> {', '.join(deps) if deps else 'нет зависимостей'}")
        else:
            print("Зависимости не найдены")
    
    except Exception as e:
        print(f"Ошибка построения графа: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()