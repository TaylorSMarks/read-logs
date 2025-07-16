from setuptools import setup

setup(
    name='read-logs',
    version='0.1.0',
    url='https://github.com/TaylorSMarks/read-logs/',
    author='Taylor S. Marks',
    author_email='taylor@marksfam.com',
    description='A python tool/app for viewing json based logs',
    keywords = 'json logs logstash',
    py_modules=['readLogs'],
    platforms='any',
    install_requires=['tksheet'],
    classifiers=[
        'Intended Audience :: Developers'
    ],
)
