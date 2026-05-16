"""Setup configuration for QRandLab package."""

from setuptools import setup, find_packages

setup(
    name="qrandlab",
    version="1.0",
    description="Comprehensive Software for Managing, Preprocessing, Extracting and Statistical Testing of RNG Files",
    author="M. H. Moradi",
    author_email="m.moradi1379@gmail.com",
    url= "https://github.com/MHMoradi79/QRandLab",
    long_description=open("README.md").read(),
    packages=find_packages(),
    python_requires=">=3.8",
    license="MIT License",
    install_requires = [
        "ttkbootstrap>=1.14.0",
        "numpy>=2.2",
        "scipy>=1.14",
        "matplotlib>=3.10",
        "requests>=2.25",
        "Jinja2>=3.0",
        "tkinterweb>=4.0",       
        "Pillow>=11.0",            
        "MarkupSafe>=3.0",
    ],

    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
)
