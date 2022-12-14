#!/usr/bin/python3
import os
import tempfile
import shutil
from setuptools import setup, find_packages
from setuptools.command.install import install

DESKTOP_ARCH = 'vsor.desktop'
APPLICATIONS_SYSTEM = '/usr/share/applications/'
APPLICATIONS_USER = os.path.join(os.environ['HOME'], '.local/share/applications/')

class PostInstalacion(install):
	def run(self):
		carpeta = APPLICATIONS_USER if self.user else APPLICATIONS_SYSTEM
		try:
			print('os.makedirs(%s)...' % carpeta, end='')
			os.makedirs(carpeta)
			print('\t done.')
		except FileExistsError:
			print('\t FileExistsError.')
			pass

		# FIXME ¿mover a build?
		# generar archivo de completado a partir de plantilla
		with open(DESKTOP_ARCH, 'r') as f:
			plantilla = f.read()

		arch_tmp = tempfile.mktemp()
		with open(arch_tmp, 'w') as f:
			f.write(plantilla % (
				os.path.join(os.environ['HOME'], '.local/bin/') if self.user else '/usr/bin/'
			))

		# copiar archivo
		print('shutil.copy("%s", os.path.join(carpeta, "vsor.desktop"))...' % arch_tmp, end='')
		shutil.copy(arch_tmp, os.path.join(carpeta, 'vsor.desktop'))
		print('\t done.')
	

		install.run(self)
setup(
	name='vsor',
	version='0.8',
	packages=find_packages(),
	cmdclass={
		'install': PostInstalacion,
	},
	entry_points={
		'console_scripts': [
			'vsor = vsor:main',
		]
	},
	include_package_data=True
)