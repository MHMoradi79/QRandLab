# Third-Party Components

This folder contains all third-party software, binaries, source archives, and license information
used by this project. Each subfolder is organized by purpose to keep the project transparent,
auditable, and compliant with applicable open-source and proprietary license terms.

## Folder structure

third_party:
- bin: Executables and dynamic libraries used by the application
- src: Original source code or source archives for third-party components
- licenses: License texts and copyright notices
- THIRD_PARTY_NOTICES.md: Summary of all third-party attributions and license types
- README.md: This file

### 1. `bin/`
Contains compiled executables or dynamic libraries used by the application at runtime.
Examples include:
- `dieharder.exe`
- `ent.exe`
- `TZ.exe`
- other .dll files

Each binary here is used **without modification**, and its license terms are described in
`licenses/` and summarized in `THIRD_PARTY_NOTICES.md`.

### 2. `src/`
Contains the original **source code** or source archives (e.g., `.zip`) of the third-party
components bundled with this project.  
This is included to comply with license requirements for redistributing source when binaries are provided.

### 3. `licenses/`
Contains the license texts and copyright notices for each component included in `bin/` or `src/`.
Each file is named after the corresponding component, for example:
- `dieharder/LICENSE.md`
- `ent/LICENSE.md`
- `cygwin/LICENSE.md`
- `toeplitz_extractor/LICENSE.md`

### 4. `THIRD_PARTY_NOTICES.md`
A concise summary of all third-party components, their licenses, and where the corresponding
source and license files are located.  
This document is intended for users, reviewers, and compliance auditors.

---

## Usage notes

- All third-party components are **used unmodified** unless explicitly noted.  
- Each component’s license is respected according to the terms stated by its author.  
- Proprietary components (e.g., hardware SDK DLLs) are redistributed **only** as allowed by
their vendor licenses and are not open-source.  
- Public-domain and permissively licensed tools are credited and attributed even if attribution
is not strictly required.

---

## Contacts and acknowledgments

If you are the author of a component included here and would like to clarify or update its
license or attribution, please contact the project maintainers.

---

_Last updated: 2026-15-05_