from pathlib import Path

from setuptools import find_packages, setup

ROOT = Path(__file__).parent
README = (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").exists() else ""

setup(
    name="roblox-afk-guard",
    version="0.1.0",
    description="Watches a Roblox window and force-quits it the moment something attacks your idle character.",
    long_description=README,
    long_description_content_type="text/markdown",
    author="H. Goldrich",
    license="MIT",
    packages=find_packages(include=["src", "src.*"]),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=[
        "mss>=9.0.1",
        "Pillow>=10.0.0",
        "numpy>=1.26.0",
        "psutil>=5.9.0",
        'pygetwindow>=0.0.9 ; sys_platform == "win32"',
        'pywin32>=306 ; sys_platform == "win32"',
        'pyobjc-framework-Quartz>=10.0 ; sys_platform == "darwin"',
    ],
    entry_points={
        "gui_scripts": [
            "roblox-afk-guard = src.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: MacOS X",
        "Environment :: Win32 (MS Windows)",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
    ],
)
