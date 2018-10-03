import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

exec(open('icebreaker/version.py').read()) # loads __version__

setup(
    name='icebreaker',
    version=__version__,
    author='Zulko',
    description='Python API for the JBEI ICE sample manager.',
    long_description=open('README.rst').read(),
    license='see LICENSE.txt',
    keywords="synthetic biology sample manager",
    packages=find_packages(exclude='docs'),
    include_package_data=True,
    install_requires=["requests", "fuzzywuzzy", "proglog", "biopython",
                      "pandas", "pyyaml", "requests-cache"])
