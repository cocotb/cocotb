# from aptk.__version__ import release
import sys, os

from setuptools import setup, find_packages

long_desc = '''
This package contains tools for easy sphinx domain creation.
'''

# Package versioning solution originally found here:
# http://stackoverflow.com/q/458550
version_path = os.path.join('sphinxcontrib', 'domaintools', '_version.py')
exec(open(version_path).read())

requires = ['Sphinx>=1.0']

setup(
    name='sphinxcontrib-domaintools',
    version=__version__,
    url='http://bitbucket.org/klorenz/sphinxcontrib-domaintools',
    download_url='http://pypi.python.org/pypi/sphinxcontrib-domaintools',
    license='BSD',
    author='Kay-Uwe (Kiwi) Lorenz',
    author_email='kiwi@franka.dyndns.org',
    description='Sphinx extension for easy domain creation.',
    long_description=long_desc,
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Documentation',
        'Topic :: Utilities',
    ],
    platforms='any',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requires,
    namespace_packages=['sphinxcontrib'],
)
