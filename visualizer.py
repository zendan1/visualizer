import xml.etree.ElementTree as ET
import os
import sys
import subprocess
import tempfile
from typing import Tuple, Dict, List

def parse_config(config_path: str) -> Tuple[str, str, str, str]:
    """
    Читает конфигурационный файл и возвращает путь к PlantUML,
    имя пакета, путь к выходному изображению и путь к базе данных пакетов.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Конфигурационный файл не найден: {config_path}")

    try:
        tree = ET.parse(config_path)
    except ET.ParseError as e:
        raise ValueError(f"Ошибка парсинга XML-файла: {e}")

    root = tree.getroot()
    plantuml_path = root.findtext('PlantUMLPath')
    package_name = root.findtext('PackageName')
    output_image_path = root.findtext('OutputImagePath')
    package_db_path = root.findtext('PackageDatabasePath')

    if not all([plantuml_path, package_name, output_image_path, package_db_path]):
        raise ValueError("Конфигурационный файл должен содержать PlantUMLPath, PackageName, OutputImagePath и PackageDatabasePath")

    if not (os.path.isfile(plantuml_path) or plantuml_path.lower().endswith('.jar')):
        raise FileNotFoundError(f"PlantUML не найден по пути: {plantuml_path}")

    if not os.path.exists(package_db_path):
        raise FileNotFoundError(f"Файл базы данных пакетов не найден: {package_db_path}")

    return plantuml_path, package_name, output_image_path, package_db_path

def parse_installed_packages(package_file: str) -> Dict[str, List[str]]:
    """
    Парсит базу данных установленных пакетов и возвращает словарь,
    где ключ — имя пакета, а значение — список его зависимостей.
    """
    if not os.path.exists(package_file):
        raise FileNotFoundError(f"Файл базы данных пакетов не найден: {package_file}")

    packages_db = {}
    current_package = None
    dependencies = []

    try:
        with open(package_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                print(f"Читается строка: {line}")  # Отладка
                if line.startswith('P:'):
                    if current_package:
                        packages_db[current_package] = dependencies
                        print(f"Добавлен пакет: {current_package} с зависимостями: {dependencies}")  # Отладка
                    current_package = line[2:]
                    dependencies = []
                elif line.startswith('D:'):
                    dep_line = line[2:]
                    deps = dep_line.split()
                    dependencies.extend(deps)
                    print(f"Добавлены зависимости: {deps}")  # Отладка
            if current_package:
                packages_db[current_package] = dependencies
                print(f"Добавлен пакет: {current_package} с зависимостями: {dependencies}")  # Отладка
    except Exception as e:
        raise IOError(f"Ошибка чтения файла пакетов: {e}")

    print(f"Полученная база пакетов: {packages_db}")  # Итоговая база для отладки
    return packages_db

def build_dependency_graph(package_name: str, packages_db: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Строит граф зависимостей для заданного пакета, включая транзитивные зависимости.
    """
    if package_name not in packages_db:
        raise ValueError(f"Пакет '{package_name}' не найден в базе данных пакетов.")

    dependency_graph = {}
    visited = set()

    def visit(pkg: str):
        if pkg not in visited:
            visited.add(pkg)
            deps = packages_db.get(pkg, [])
            dependency_graph[pkg] = deps
            for dep in deps:
                visit(dep)

    visit(package_name)
    return dependency_graph

def generate_plantuml(dependency_graph: Dict[str, List[str]]) -> str:
    """
    Генерирует код PlantUML на основе графа зависимостей.
    """
    lines = ['@startuml']
    for pkg, deps in dependency_graph.items():
        for dep in deps:
            lines.append(f'"{pkg}" --> "{dep}"')
    lines.append('@enduml')
    return '\n'.join(lines)

def generate_image(plantuml_code: str, plantuml_path: str, output_image_path: str) -> None:
    """
    Использует PlantUML для генерации PNG-изображения графа зависимостей.
    """
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.puml') as tmp:
        tmp.write(plantuml_code)
        tmp_path = tmp.name
        print(f"Временный файл PlantUML создан: {tmp_path}")  # Логирование

    try:
        # Команда для запуска PlantUML на Windows
        # PlantUML запускается через java -jar plantuml.jar
        command = ['java', '-jar', plantuml_path, '-tpng', tmp_path, '-o', os.path.dirname(output_image_path)]
        print(f"Выполняется команда: {' '.join(command)}")  # Логирование
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"PlantUML завершился с кодом: {result.returncode}")  # Логирование

        # Определяем путь к сгенерированному изображению в директории вывода
        generated_image = os.path.join(os.path.dirname(output_image_path), os.path.splitext(os.path.basename(tmp_path))[0] + '.png')
        print(f"Ожидаемый путь сгенерированного изображения: {generated_image}")  # Логирование

        if not os.path.exists(generated_image):
            raise FileNotFoundError("PlantUML не сгенерировал изображение.")

        # Перемещаем сгенерированное изображение в желаемое место (переименовываем)
        os.rename(generated_image, output_image_path)
        print(f"Изображение перемещено в: {output_image_path}")  # Логирование
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode().strip()
        print(f"PlantUML stderr: {stderr}")  # Логирование
        raise RuntimeError(f"Ошибка при выполнении PlantUML: {stderr}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            print(f"Временный файл PlantUML удалён: {tmp_path}")  # Логирование

def main():
    if len(sys.argv) != 2:
        print("Usage: python visualizer.py <config.xml>")
        sys.exit(1)
    config_path = sys.argv[1]
    try:
        plantuml_path, package_name, output_image_path, package_db_path = parse_config(config_path)
        print(f"PlantUML Path: {plantuml_path}")  # Отладка
        print(f"Package Name: {package_name}")  # Отладка
        print(f"Output Image Path: {output_image_path}")  # Отладка
        print(f"Package Database Path: {package_db_path}")  # Отладка

        packages_db = parse_installed_packages(package_db_path)
        dependency_graph = build_dependency_graph(package_name, packages_db)
        print(f"Dependency Graph: {dependency_graph}")  # Отладка
        plantuml_code = generate_plantuml(dependency_graph)
        print(f"Generated PlantUML Code:\n{plantuml_code}")  # Отладка
        generate_image(plantuml_code, plantuml_path, output_image_path)
        print(f"Граф зависимостей успешно сохранен в {output_image_path}")
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
