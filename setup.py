from setuptools import setup, find_packages

setup(
    name='logparser',
    version='0.0.1',
    description='Clarity code challenge',
    author='Fermin Martinez',
    author_email='ferkys@gmail.com',
    packages=find_packages(),
    python_requires='>=3.6.*',
    include_package_data=True,
    install_requires=[
        'dask==1.1.3',
        'distributed',
        'click==7.0'
    ],
    entry_points='''
    [console_scripts]
    logparser=logparser.parser:parser
    logparser-make=logparser.parser:makefake
''',
)
