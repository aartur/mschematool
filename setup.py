from setuptools import setup, find_packages

setup(
        name = 'mschematool',
        version = '0.9.1',
        packages = ['mschematool', 'mschematool.executors'],
        install_requires = [
            'click==6.7',
            'sqlparse==0.2.4',
        ],
        entry_points = {
            'console_scripts': [
                'mschematool = mschematool.cli:main',
            ]
        },
        extras_require = {
            'postgresql': ['psycopg2'],
            'cassandra': ['cassandra-driver'],
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
        classifiers = [
            'Topic :: Database',
            'Environment :: Console',
            'License :: OSI Approved :: BSD License',
            'Programming Language :: Python :: 2.7',
        ],
)
