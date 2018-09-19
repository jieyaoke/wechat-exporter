import setuptools

with open("README.rst", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='wechat-exporter',
    version='0.1.1',
    url='https://github.com/jieyaoke/wechat-exporter',
    license='MIT',
    author='jieyaoke',
    author_email='jieyao.ke@gmail.com',
    description='Wechat data export tool',
    packages=setuptools.find_packages(),
    zip_safe=False,
    platforms='any',
    install_requires=[
        'biplist',
        'xmltodict',
        'jinja2',
    ],
    entry_points="""
    [console_scripts]
    wexp = we.run:main
    """,
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ]
)
