from setuptools import setup, find_packages

VERSION = '0.2.0' 
DESCRIPTION = 'Python compartment modelling framework'
LONG_DESCRIPTION = 'Classes for creating stochastic compartment models and running Monte Carlo simulations.'

# Setting up
setup(
        name="pycomod", 
        version=VERSION,
        author="Stephen Okazawa",
        author_email="okazawa.s@gmail.com",
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        packages=find_packages(),
        install_requires=['numpy', 'matplotlib', 'pandas', 'bokeh>=2.4.1'],
        
        keywords=['python', 'sir', 'model', 'simulation'],
        classifiers= [
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Education",
            "Programming Language :: Python :: 3",
            "Operating System :: Microsoft :: Windows",
        ]
)
