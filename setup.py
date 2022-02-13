import setuptools

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name='dinamopy',
    version='0.1.0',
    author='Rasim Andiran',
    author_email='rasimandiran@gmail.com',
    description='DynamoDB wrapper',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/rasimandiran/dinamopy',
    classifiers=[        
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent'
    ],
    package_dir={'dinamopy': 'dinamopy'},
    packages=['dinamopy'],
    python_requires='>=3.6',
)