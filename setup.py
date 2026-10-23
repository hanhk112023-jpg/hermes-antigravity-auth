from setuptools import setup, find_packages

setup(
    name="hermes-deepseek2api",
    version="2.0.0",
    packages=find_packages(include=["deepseek_auth*"]),
    package_data={"deepseek_auth": ["wasm/*.wasm"]},
    install_requires=[
        "httpx>=0.24.0",
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "hermes-deepseek = deepseek_auth.cli:main",
        ],
    },
)
