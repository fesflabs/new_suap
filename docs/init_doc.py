import ast
import sys
import os

from contextlib import redirect_stdout
from tqdm import tqdm


BASE_DOC_PATH = './modules'
EXCLUDE_NAMES = ['apps', 'features', 'fixtures', 'migrations', 'test', 'urls']


def top_level_documentable(elements):
    return [e for e in elements if isinstance(e, ast.FunctionDef) or isinstance(e, ast.ClassDef)]


def create_rst_file(path_name, base_module, files_name):
    def write_rst(base_path, files_name):
        path_name = os.path.join(BASE_DOC_PATH, base_module)
        rst_name = f"{'_'.join(base_path)}.rst"

        if len(base_path) == 0:
            rst_name = f"{base_module}.rst"

        if not os.path.exists(path_name):
            os.mkdir(path_name)

        title = f"Submódulo {'.'.join(base_path)}"

        with open(os.path.join(path_name, rst_name), 'w') as fd, redirect_stdout(fd):
            print(title)
            print('-' * len(title))

            for file in files_name:
                module_name = f"{'.'.join(base_path + [file[:file.rfind('.')]])}"

                print(f'\n{module_name}')
                print('~' * len(module_name))

                if file.startswith('__init__'):
                    if module_name.rfind('.') < 0:
                        print(f".. automodule:: {base_module}")
                    else:
                        print(f".. automodule:: {base_module}.{module_name[:module_name.rfind('.')]}")
                else:
                    print(f'.. automodule:: {base_module}.{module_name}')
                print('    :members:')

    write_rst(path_name, files_name)


def find_modules(base_path, base_module):
    modules = []
    for dir_path, dir_names, files_name in tqdm(os.walk(base_path)):
        files_to_doc = []
        for file in files_name:
            if file.endswith('py'):
                files_to_doc.append(file)
        if files_to_doc:
            skipped = False
            for exclude_name in EXCLUDE_NAMES:
                if exclude_name in dir_path:
                    skipped = True
                    break
            if not skipped:
                base_name = dir_path[dir_path.find(base_module):].split('/')
                modules.append(base_name)
                create_rst_file(base_name[1:], base_module, sorted(files_to_doc))

    with open(os.path.join(BASE_DOC_PATH, base_module, 'index.rst'), 'w') as fd, redirect_stdout(fd):
        print(base_module.title())
        print('=' * len(base_module))
        print('\n.. toctree::\n    :maxdepth: 1\n')

        for module in sorted(modules):
            module_file = ''
            if len(module) == 1:
                module_file = module[0]
            else:
                module_file = '_'.join(module[1:])
            print(f'    {module_file}.rst')


def main():
    find_modules(sys.argv[1], sys.argv[2])


if __name__ == '__main__':
    main()
