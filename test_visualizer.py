import unittest
from unittest.mock import patch, mock_open, MagicMock
import subprocess
import os
import sys
from visualizer import (
    parse_config,
    parse_installed_packages,
    build_dependency_graph,
    generate_plantuml,
    generate_image,
    main
)

class TestVisualizer(unittest.TestCase):

    @patch('visualizer.ET.parse')
    @patch('visualizer.os.path.isfile')
    @patch('visualizer.os.path.exists')
    def test_parse_config_success(self, mock_exists, mock_isfile, mock_parse):
        # Настройка мока
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_tree = MagicMock()
        mock_root = MagicMock()
        mock_root.findtext.side_effect = [
            'C:\\PlantUML\\plantuml.jar',
            'bash',
            'C:\\Users\\Пользователь\\Desktop\\конфигурационка\\dependencies.png',
            'C:\\Users\\Пользователь\\Desktop\\конфигурационка\\installed'
        ]
        mock_tree.getroot.return_value = mock_root
        mock_parse.return_value = mock_tree

        # Вызов функции
        result = parse_config('config.xml')

        # Проверка результатов
        expected = (
            'C:\\PlantUML\\plantuml.jar',
            'bash',
            'C:\\Users\\Пользователь\\Desktop\\конфигурационка\\dependencies.png',
            'C:\\Users\\Пользователь\\Desktop\\конфигурационка\\installed'
        )
        self.assertEqual(result, expected)
        mock_parse.assert_called_once_with('config.xml')

    @patch('visualizer.os.path.exists', return_value=False)
    def test_parse_config_file_not_found(self, mock_exists):
        with self.assertRaises(FileNotFoundError) as context:
            parse_config('nonexistent_config.xml')
        self.assertIn("Конфигурационный файл не найден: nonexistent_config.xml", str(context.exception))

    @patch('visualizer.ET.parse')
    @patch('visualizer.os.path.isfile', return_value=False)
    @patch('visualizer.os.path.exists', return_value=True)
    def test_parse_config_plantuml_not_found(self, mock_exists, mock_isfile, mock_parse):
        mock_tree = MagicMock()
        mock_root = MagicMock()
        mock_root.findtext.side_effect = [
            'C:\\PlantUML\\plantuml_not_jar.exe',  # Не оканчивается на .jar
            'bash',
            'C:\\Users\\Пользователь\\Desktop\\конфигурационка\\dependencies.png',
            'C:\\Users\\Пользователь\\Desktop\\конфигурационka\\installed'
        ]
        mock_tree.getroot.return_value = mock_root
        mock_parse.return_value = mock_tree

        with self.assertRaises(FileNotFoundError) as context:
            parse_config('config.xml')
        self.assertIn("PlantUML не найден по пути: C:\\PlantUML\\plantuml_not_jar.exe", str(context.exception))

    @patch('builtins.open', new_callable=mock_open, read_data="P:bash\nD:libc readline\nP:libc\nD:\nP:readline\nD:libc")
    @patch('visualizer.os.path.exists', return_value=True)
    def test_parse_installed_packages_success(self, mock_exists, mock_file):
        result = parse_installed_packages('packages.db')
        expected = {
            'bash': ['libc', 'readline'],
            'libc': [],
            'readline': ['libc']
        }
        self.assertEqual(result, expected)
        mock_file.assert_called_once_with('packages.db', 'r', encoding='utf-8')

    @patch('builtins.open', new_callable=mock_open, read_data="Invalid content")
    @patch('visualizer.os.path.exists', return_value=True)
    def test_parse_installed_packages_malformed(self, mock_exists, mock_file):
        # Функция пропускает некорректные строки и возвращает пустой словарь
        result = parse_installed_packages('packages.db')
        expected = {}
        self.assertEqual(result, expected)

    @patch('visualizer.os.path.exists', return_value=False)
    def test_parse_installed_packages_file_not_found(self, mock_exists):
        with self.assertRaises(FileNotFoundError) as context:
            parse_installed_packages('nonexistent_packages.db')
        self.assertIn("Файл базы данных пакетов не найден: nonexistent_packages.db", str(context.exception))

    def test_build_dependency_graph_success(self):
        packages_db = {
            'bash': ['libc', 'readline'],
            'libc': [],
            'readline': ['libc']
        }
        expected_graph = {
            'bash': ['libc', 'readline'],
            'libc': [],
            'readline': ['libc']
        }
        result = build_dependency_graph('bash', packages_db)
        self.assertEqual(result, expected_graph)

    def test_build_dependency_graph_nonexistent_package(self):
        packages_db = {
            'bash': ['libc'],
            'libc': []
        }
        with self.assertRaises(ValueError) as context:
            build_dependency_graph('nonexistent', packages_db)
        self.assertIn("Пакет 'nonexistent' не найден в базе данных пакетов.", str(context.exception))

    def test_build_dependency_graph_with_circular_dependency(self):
        packages_db = {
            'A': ['B'],
            'B': ['C'],
            'C': ['A']  # Циклическая зависимость
        }
        expected_graph = {
            'A': ['B'],
            'B': ['C'],
            'C': ['A']
        }
        result = build_dependency_graph('A', packages_db)
        self.assertEqual(result, expected_graph)

    def test_generate_plantuml(self):
        dependency_graph = {
            'bash': ['libc', 'readline'],
            'libc': [],
            'readline': ['libc']
        }
        expected_puml = (
            "@startuml\n"
            '"bash" --> "libc"\n'
            '"bash" --> "readline"\n'
            '"readline" --> "libc"\n'
            "@enduml"
        )
        result = generate_plantuml(dependency_graph)
        self.assertEqual(result, expected_puml)

    @patch('visualizer.os.remove')
    @patch('builtins.print')
    @patch('visualizer.tempfile.NamedTemporaryFile')
    @patch('visualizer.os.rename')
    @patch('visualizer.os.path.exists')
    @patch('visualizer.subprocess.run')
    def test_generate_image_success(self, mock_run, mock_exists, mock_rename, mock_tempfile, mock_print, mock_remove):
        # Настройка мока временного файла
        mock_tmp = MagicMock()
        mock_tmp.name = 'C:\\Users\\73B5~1\\AppData\\Local\\Temp\\tmpjbs2s7jc.puml'
        mock_named_tempfile = MagicMock()
        mock_named_tempfile.__enter__.return_value = mock_tmp
        mock_named_tempfile.__exit__.return_value = None
        mock_tempfile.return_value = mock_named_tempfile

        # Настройка мока subprocess.run
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=b'', stderr=b'')

        # Настройка существования сгенерированного изображения
        def exists_side_effect(path):
            return path in [
                'C:\\Users\\73B5~1\\AppData\\Local\\Temp\\tmpjbs2s7jc.puml',
                'C:\\Users\\Пользователь\\Desktop\\конфигурационka\\tmpjbs2s7jc.png'
            ]

        mock_exists.side_effect = exists_side_effect

        # Вызов функции
        generate_image(
            '@startuml\n"bash" --> "libc"\n"bash" --> "readline"\n"readline" --> "libc"\n@enduml',
            'C:\\PlantUML\\plantuml.jar',
            'C:\\Users\\Пользователь\\Desktop\\конфигурационka\\dependencies.png'
        )

        # Проверка вызовов
        mock_tempfile.assert_called_once_with('w', delete=False, suffix='.puml')
        mock_run.assert_called_once_with(
            [
                'java',
                '-jar',
                'C:\\PlantUML\\plantuml.jar',
                '-tpng',
                'C:\\Users\\73B5~1\\AppData\\Local\\Temp\\tmpjbs2s7jc.puml',
                '-o',
                'C:\\Users\\Пользователь\\Desktop\\конфигурационka'
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        expected_generated_image = 'C:\\Users\\Пользователь\\Desktop\\конфигурационka\\tmpjbs2s7jc.png'
        mock_rename.assert_called_once_with(expected_generated_image, 'C:\\Users\\Пользователь\\Desktop\\конфигурационka\\dependencies.png')
        mock_print.assert_called_with(f"Временный файл PlantUML создан: {mock_tmp.name}")
        # Проверка удаления временного файла
        mock_tmp.write.assert_called_once_with(
            '@startuml\n"bash" --> "libc"\n"bash" --> "readline"\n"readline" --> "libc"\n@enduml'
        )
        mock_remove.assert_called_once_with(mock_tmp.name)

    @patch('visualizer.os.remove')
    @patch('builtins.print')
    @patch('visualizer.tempfile.NamedTemporaryFile')
    @patch('visualizer.os.rename')
    @patch('visualizer.os.path.exists', return_value=True)
    @patch('visualizer.subprocess.run', side_effect=subprocess.CalledProcessError(1, 'cmd', stderr=b'Error'))
    def test_generate_image_subprocess_error(self, mock_run, mock_exists, mock_rename, mock_tempfile, mock_print, mock_remove):
        # Настройка мока временного файла
        mock_tmp = MagicMock()
        mock_tmp.name = 'temp.puml'
        mock_named_tempfile = MagicMock()
        mock_named_tempfile.__enter__.return_value = mock_tmp
        mock_named_tempfile.__exit__.return_value = None
        mock_tempfile.return_value = mock_named_tempfile

        # Вызов функции и проверка исключения
        with self.assertRaises(RuntimeError) as context:
            generate_image(
                '@startuml\n@enduml',
                'C:\\PlantUML\\plantuml.jar',
                'C:\\Users\\Пользователь\\Desktop\\конфигурационka\\dependencies.png'
            )
        self.assertIn('Ошибка при выполнении PlantUML: Error', str(context.exception))

        # Проверка вызовов
        mock_run.assert_called_once_with(
            [
                'java',
                '-jar',
                'C:\\PlantUML\\plantuml.jar',
                '-tpng',
                'temp.puml',
                '-o',
                'C:\\Users\\Пользователь\\Desktop\\конфигурационka'
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        mock_rename.assert_not_called()
        mock_print.assert_called_with(f"Временный файл PlantUML создан: {mock_tmp.name}")
        # Проверка удаления временного файла
        mock_tmp.write.assert_called_once_with('@startuml\n@enduml')
        mock_remove.assert_called_once_with(mock_tmp.name)

    @patch('visualizer.sys.exit', side_effect=SystemExit(1))
    @patch('visualizer.parse_config')
    @patch('visualizer.parse_installed_packages')
    @patch('visualizer.build_dependency_graph')
    @patch('visualizer.generate_plantuml')
    @patch('visualizer.generate_image')
    @patch('builtins.print')
    def test_main_success(self, mock_print, mock_generate_image, mock_generate_plantuml, mock_build_dependency_graph, mock_parse_installed_packages, mock_parse_config, mock_exit):
        # Настройка мока parse_config
        mock_parse_config.return_value = (
            'C:\\PlantUML\\plantuml.jar',
            'bash',
            'C:\\Users\\Пользователь\\Desktop\\конфигурационka\\dependencies.png',
            'C:\\Users\\Пользователь\\Desktop\\конфигурационka\\installed'
        )

        # Настройка мока parse_installed_packages
        mock_parse_installed_packages.return_value = {
            'bash': ['libc', 'readline'],
            'libc': [],
            'readline': ['libc']
        }

        # Настройка мока build_dependency_graph
        mock_build_dependency_graph.return_value = {
            'bash': ['libc', 'readline'],
            'libc': [],
            'readline': ['libc']
        }

        # Настройка мока generate_plantuml
        mock_generate_plantuml.return_value = (
            '@startuml\n'
            '"bash" --> "libc"\n'
            '"bash" --> "readline"\n'
            '"readline" --> "libc"\n'
            '@enduml'
        )

        # Настройка мока generate_image
        mock_generate_image.return_value = None

        # Настройка аргументов командной строки
        test_args = ['visualizer.py', 'config.xml']
        with patch.object(sys, 'argv', test_args):
            main()

        # Проверка вызовов
        mock_parse_config.assert_called_once_with('config.xml')
        mock_parse_installed_packages.assert_called_once_with('C:\\Users\\Пользователь\\Desktop\\конфигурационka\\installed')
        mock_build_dependency_graph.assert_called_once_with('bash', {
            'bash': ['libc', 'readline'],
            'libc': [],
            'readline': ['libc']
        })
        mock_generate_plantuml.assert_called_once_with({
            'bash': ['libc', 'readline'],
            'libc': [],
            'readline': ['libc']
        })
        mock_generate_image.assert_called_once_with(
            '@startuml\n"bash" --> "libc"\n"bash" --> "readline"\n"readline" --> "libc"\n@enduml',
            'C:\\PlantUML\\plantuml.jar',
            'C:\\Users\\Пользователь\\Desktop\\конфигурационka\\dependencies.png'
        )
        mock_print.assert_any_call("PlantUML Path: C:\\PlantUML\\plantuml.jar")
        mock_print.assert_any_call("Package Name: bash")
        mock_print.assert_any_call("Output Image Path: C:\\Users\\Пользователь\\Desktop\\конфигурационka\\dependencies.png")
        mock_print.assert_any_call("Package Database Path: C:\\Users\\Пользователь\\Desktop\\конфигурационka\\installed")
        mock_print.assert_any_call("Generated PlantUML Code:")
        mock_print.assert_any_call('@startuml\n"bash" --> "libc"\n"bash" --> "readline"\n"readline" --> "libc"\n@enduml')
        mock_print.assert_any_call("Граф зависимостей успешно сохранен в C:\\Users\\Пользователь\\Desktop\\конфигурационka\\dependencies.png")
        mock_exit.assert_not_called()

    @patch('visualizer.sys.exit', side_effect=SystemExit(1))
    @patch('builtins.print')
    def test_main_invalid_arguments(self, mock_print, mock_exit):
        test_args = ['visualizer.py']  # Недостаточно аргументов
        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit) as context:
                main()
        mock_print.assert_called_with("Usage: python visualizer.py <config.xml>")
        mock_exit.assert_called_once_with(1)

    @patch('visualizer.sys.exit', side_effect=SystemExit(1))
    @patch('visualizer.parse_config', side_effect=Exception('Config Error'))
    @patch('builtins.print')
    def test_main_parse_config_exception(self, mock_print, mock_parse_config, mock_exit):
        test_args = ['visualizer.py', 'config.xml']
        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit) as context:
                main()
        mock_print.assert_called_with("Ошибка: Config Error")
        mock_exit.assert_called_once_with(1)

    @patch('visualizer.sys.exit', side_effect=SystemExit(1))
    @patch('visualizer.parse_installed_packages', side_effect=IOError('Read Error'))
    @patch('visualizer.parse_config')
    @patch('builtins.print')
    def test_main_parse_installed_packages_exception(self, mock_print, mock_parse_config, mock_parse_installed_packages, mock_exit):
        mock_parse_config.return_value = (
            'C:\\PlantUML\\plantuml.jar',
            'bash',
            'C:\\Users\\Пользователь\\Desktop\\конфигурационka\\dependencies.png',
            'C:\\Users\\Пользователь\\Desktop\\конфигурационka\\installed'
        )
        test_args = ['visualizer.py', 'config.xml']
        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit) as context:
                main()
        mock_print.assert_called_with("Ошибка: Read Error")
        mock_exit.assert_called_once_with(1)

    @patch('visualizer.sys.exit', side_effect=SystemExit(1))
    @patch('visualizer.build_dependency_graph', side_effect=ValueError('Dependency Error'))
    @patch('visualizer.parse_installed_packages')
    @patch('visualizer.parse_config')
    @patch('builtins.print')
    def test_main_build_dependency_graph_exception(self, mock_print, mock_parse_config, mock_parse_installed_packages, mock_build_dependency_graph, mock_exit):
        mock_parse_config.return_value = (
            'C:\\PlantUML\\plantuml.jar',
            'bash',
            'C:\\Users\\Пользователь\\Desktop\\конфигурационka\\dependencies.png',
            'C:\\Users\\Пользователь\\Desktop\\конфигурационka\\installed'
        )
        mock_parse_installed_packages.return_value = {
            'bash': ['libc', 'readline'],
            'libc': [],
            'readline': ['libc']
        }
        test_args = ['visualizer.py', 'config.xml']
        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit) as context:
                main()
        mock_print.assert_called_with("Ошибка: Dependency Error")
        mock_exit.assert_called_once_with(1)

if __name__ == '__main__':
    unittest.main()
