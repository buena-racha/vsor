#!/usr/bin/python3
from setuptools import setup, find_packages

setup(
	name='vsor',
	version='0.1',
	packages=find_packages(),
	# scripts=['rin.py'],
	entry_points={
		'console_scripts': [
			'vsor = vsor:main',
		]
	},
	include_package_data=True
)