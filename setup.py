from setuptools import setup, find_packages

setup(
        name = 'mschematool',
        version = '0.6.4',
        packages = ['mschematool', 'mschematool.executors'],
        install_requires = ['click==3.3'],
        entry_points = {
            'console_scripts': [
                'mschematool = mschematool.cli:main',
            ]
        },
        extras_require = {
            'postgresql': ['psycopg2'],
            'cassandra': ['cassandra-driver', 'blist'],
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
            'Programming Language :: Python :: 3.4',
        ],
)
