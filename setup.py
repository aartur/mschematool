from setuptools import setup, find_packages

setup(
        name = 'mschematool',
        version = '0.6.1',
        py_modules = ['mschematool'],
        install_requires = ['click==3.3'],
        entry_points = {
            'console_scripts': [
                'mschematool = mschematool:main',
            ]
        },

        author = 'Artur Siekielski',
        author_email = 'artur.siekielski@vhex.net',
        description = 'Minimal database schema migrations tool',
        long_description = '''
See description at `<https://github.com/aartur/mschematool>`_.
        ''',
        license = 'BSD',
        keywords = 'database schema migrations postgresql postgres cassandra',
        url = 'https://github.com/aartur/mschematool',
)
