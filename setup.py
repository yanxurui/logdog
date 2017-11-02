from setuptools import setup

setup(
    name="logdog",
    version="0.0.1",
    author="Xurui Yan",
    author_email="yxr1993@gmail.com",
    description='a real time logs monitor based on inotify',
    license="MIT License",
    keywords="log monitor",
    url="https://github.com/yanxurui/logdog",
    package_dir = {'': 'src'},
    py_modules=['logdog'],
    platforms=['Linux'],
    install_requires=[
        'glob2>=0.6',
        'pyinotify>=0.9.6'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Environment :: Console',
        'Topic :: Utilities'
    ]
)
