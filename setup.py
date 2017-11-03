from setuptools import setup

setup(
    name="logdogs",
    version="0.0.1",
    author="Xurui Yan",
    author_email="yxr1993@gmail.com",
    description='a multiple logs monitor, see Github README for details',
    license="MIT License",
    keywords="log monitor",
    url="https://github.com/yanxurui/logdog",
    package_dir = {'logdogs': 'src'},
    packages=['logdogs'],
    platforms=['Linux'],
    install_requires=[
        'glob2>=0.6',
        'python-daemon>=2.1.2'
    ],
    entry_points={
        'console_scripts': [
            'logdogs=logdogs:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Environment :: Console',
        'Topic :: Utilities'
    ]
)
