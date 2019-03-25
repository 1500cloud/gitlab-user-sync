#!/usr/bin/env python3

from setuptools import setup

setup(name='gitlab_user_sync',
      version='1.0.dev',
      description='synchronises users between G Suite and a GitLab group',
      url='https://github.com/1500cloud/gitlab-user-sync/',
      author='Chris Northwood',
      author_email='chris.northwood@1500cloud.com',
      license='GNU General Purpose License v3',
      packages=['gitlab_user_sync'],
      install_requires=[
            'google-api-python-client ~= 1.7',
            'google-auth ~= 1.6',
            'python-gitlab ~= 1.8',
      ],
      scripts=['bin/sync-gitlab-users'])
