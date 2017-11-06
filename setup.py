from setuptools import setup

setup(
    name="logdogs",
    version="0.3rc1",
    author="Xurui Yan",
    author_email="yxr1993@gmail.com",
    description='A daemon to monitor keywords in any log files specified by glob pattern',
    long_description=open('README.rst').read(),
    license="MIT License",
    keywords="log monitor",
    url="https://github.com/yanxurui/logdogs",
    package_dir = {'': 'src'},
    py_modules=['logdogs'],
    platforms=['Linux'],
    install_requires=[
        'glob2>=0.6',
        'python-daemon>=2.1.2'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Environment :: Console',
        'Topic :: Utilities'
    ]
)
