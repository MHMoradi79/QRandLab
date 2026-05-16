# QRandLab Toolbox

QRandLab is a lightweight, Python-based toolbox for **processing and evaluating random-number sequences** from both quantum and pseudo-random sources. It supports multiple file formats, conversion and slicing tools, and multi-file inputs. The toolbox implements **bias-reduction techniques** (Von Neumann, XOR folding, Toeplitz extraction) and integrates standard statistical test suites such as **ENT**, **NIST SP 800-22 rev 1a**, **Dieharder**, **Borel normality**, and **autocorrelation**, with results available as concise summaries or detailed HTML reports.

QRandLab also includes modules for:

- Accessing **quantum entropy** from online services  
- Interfacing with a **commercial QRNG hardware device**  
- Producing **PRNG output** via over seventy well-studied algorithms  

It is motivated by the practical challenges faced by **experimental quantum physicists** (e.g. in quantum sensing and communication) when analyzing quantum-generated randomness, especially in interdisciplinary settings where traditional cryptographic testing tools are complex, fragmented, or OS-dependent. By offering an accessible, unified, and reproducible platform, QRandLab helps **bridge the usability gap** and streamlines randomness evaluation across research domains.


This README gives a **high-level overview** of:

- The **project structure**
- The **different ways you can use QRandLab**:
  - As a **standalone executable**
  - As a **Python application from source**
  - As a **Python module/package** in your own code
  - As a **rebuildable executable** via PyInstaller
- **Example data** directory
- **Third party** directory
- **LICENSE** file


---

## Project Structure
```text
QRandLab/
├─ dist/                   # Final executable for end users
├─ example_data/           # Example inputs and workflows
├─ src/
│  └─ ...                  # Application source code
│     └─ main.py           # Main entry point (runs the project)
├─ third_party/
│  ├─ ...                  # Third-party source code, 
│  └─ LICENSES             # Licenses for bundled components
├─ qrandlab.spec           # PyInstaller spec file (build recipe for the EXE)
├─ pyinstaller.txt         # Example PyInstaller command to build the app
├─ requirements.txt        # Python dependencies required to run from source
├─ setup.py                # Packaging configuration for use as a Python module
└─ README.md               # This high-level project description 
```

## Ways to Use QRandLab
### 1. As a Standalone Executable (End-User Mode)

If you just want to **run the toolbox** without dealing with Python or dependencies:

1. Go to the `dist/` folder.
2. Locate the main executable:
   - On Windows, this will typically be like: `QRandLab.exe`.
3. Run it:
   - Double-click the executable, **or**
   - Launch it from a terminal / command prompt.

> This mode is ideal for **non-developers** or anyone who simply wants to use QRandLab as an application.

---

### 2. As a Python Application (Run from Source)

If you want to **inspect or modify the source code** or run the app directly under Python:

#### Install the required packages

From the project root:
```bash
pip install -r requirements.txt
```
Run the application:

```bash
   python src/main.py
```
This mode is recommended if you:

- Want to debug or extend QRandLab
- Prefer to run everything inside a Python environment
- Need to integrate QRandLab with other custom logic at the script level
----
### 3. As a Python Module (Library Usage)
The presence of **setup.py** means you can install QRandLab as a package and use its functionality programmatically.

#### Install the required packages

From the project root:
```bash
pip install -r requirements.txt
```

#### Install the QRandLab
From the project root:

```bash
   # Development (editable) install
   pip install -e .

   # or standard install
   pip install .
```
Import and use in Python:
```python
   import qrandlab
```
Use this mode if you want to:

> Integrate QRandLab’s randomness tests into your own scripts
Automate workflows using QRandLab from within a larger Python project
Build custom pipelines that call QRandLab functions.

----

### 4. As a Rebuildable Executable (PyInstaller)
If you want to build your own executable from the source code (e.g. after editing), you can use the provided PyInstaller configuration.

#### Using qrandlab.spec

qrandlab.spec is the PyInstaller spec file that defines:
- Which scripts to include
- Which data files to bundle
- How to structure the final executable

A typical build command (from the project root) is:
```bash
pyinstaller qrandlab.spec
```
This will:

- Put intermediate build artifacts in build/
- Put the final executable bundle in dist/

#### Using pyinstaller.txt
The file pyinstaller.txt contains example command for PyInstaller.
Open it and run the provided command.

Use this mode if you:
- Need a customized EXE
- Have modified the source and want an updated end-user build
- Want to distribute QRandLab as a standalone application after your changes

----

## Example Data
The example_data/ directory contains:

- Sample random data files
- Example workflows and final report
- A demonstration of how to use the toolbox end-to-end

You can use this folder to:

- Verify that your installation works correctly
- Learn how to structure your input files and interpret the outputs
- Reproduce a known workflow as a reference

----

## Third-Party Components
The third_party/ directory includes:

- Third-party source code, libraries, and binaries used internally
- Corresponding license files or notices
- helper executables for external test suites (e.g. Dieharder, ENT, etc.)

----

## License
QRandLab is licensed under the **MIT License**.  
See the `LICENSE.txt` file for details.

This project includes third-party components in the `third_party/` directory.
Each component retains its original license, which is included in that directory
and summarized in `third_party/THIRD_PARTY_NOTICES.md`.

