from setuptools import setup, find_packages

setup(
       name="ncbi-api-client",
       version="0.1.0",
       description="Rate-limited NCBI E-utilities API client with local caching",
       author="Xavier Ramos",
       author_email="xarnyc@protonmail.com",
       packages=find_packages(),
       install_requires=[
           "requests>=2.31.0",
           "pydantic>=2.5.0",
           "click>=8.1.0",
           "tenacity>=8.2.0",
       ],
       extras_require={
           "dev": ["pytest>=7.4.0", "black>=23.0.0", "mypy>=1.7.0"],
       },
       python_requires=">=3.9",
       entry_points={
           "console_scripts": [
               "ncbi-fetch=ncbi_client.cli:main",  # adjust module path if needed
           ],
       },
   )