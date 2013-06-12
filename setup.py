#!/usr/bin/env python

from setuptools import setup, find_packages
from distutils.command.install import install as DistutilsInstall

class CocotbInstall(DistutilsInstall):
    def run(self):
        print("Build support libs\n")
        DistutilsInstall.run(self)

setup(
    name='cocotb',
    version='0.0.1',
    description='Coroutine Cosimulation Test Bench',
    author='Potential Ventures',
    author_email='coctob@potentialventures.com',
    packages=find_packages('.'),
    cmdclass={'install': CocotbInstall},
    include_package_data = True,
    long_description="""\
      Cocotb is a coroutines-based cosimulation test bench framework for rapid
      development of FPGA components
      """,
      classifiers=[
          "License :: BSD",
          "Programming Language :: Python",
          "Development Status :: 4 - Beta",
          "Intended Audience :: Developers",
          "Topic :: Internet",
      ],
      keywords='simulation',
      license='BSD',
      )
