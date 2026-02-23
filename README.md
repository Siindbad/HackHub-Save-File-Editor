![Verification Suite](https://img.shields.io/badge/Verification%20Suite-Passing-brightgreen) ![License](https://img.shields.io/badge/License-MIT-8B0000) ![Languages](https://img.shields.io/badge/Languages-Python-3776AB) [![Release Build](https://github.com/Siindbad/HackHub-Save-File-Editor/actions/workflows/release-build-sign.yml/badge.svg?branch=main)](https://github.com/Siindbad/HackHub-Save-File-Editor/actions/workflows/release-build-sign.yml)



| <img align="left" alt="DISCORD" src="https://img.shields.io/badge/DISCORD-5865F2?style=for-the-badge&labelColor=0F172A"> |
|---|
| [SIN.NETWORK](https://discord.gg/kpFXrtyr2Z) |



| <img align="left" alt="RELEASES" src="https://img.shields.io/badge/RELEASES-2563EB?style=for-the-badge&labelColor=0F172A"> |
|---|
| [Download latest release](https://github.com/Siindbad/HackHub-Save-File-Editor/releases/latest) |



| <img align="left" alt="REMINDER" src="https://img.shields.io/badge/REMINDER-0D9488?style=for-the-badge&labelColor=0F172A"> |
|---|
| 1. Use the in-app README for quick usage guidance.<br>2. The program supports automatic update checks and a manual Update button to keep you on the latest version. |


| <img align="left" alt="USAGE" src="https://img.shields.io/badge/USAGE-2563EB?style=for-the-badge&labelColor=0F172A"> |
|---|
| Sin EDITOR is designed for quick, practical save-file fixes. It helps players and community helpers resolve common issues faster, with focused editing and clearer error guidance.<br><br>You can edit many values in a save file, but the safest use is targeted corrections (for example: ports, missing services, credentials, and similar recovery fixes). Directly changing device identities or IP structures is possible, but not recommended unless you know exactly what you are doing.<br><br>Example:<br>If a router is showing a 404 page because a port is incorrect, open the save, go to the `NETWORK` section, locate the affected public IP entry, correct the port (for example `22` to `80`), then export and import the updated save. |


| <img align="left" alt="CHANGE LOGS" src="https://img.shields.io/badge/CHANGE%20LOGS-5B21B6?style=for-the-badge&labelColor=0F172A"> |
|---|
| **[ Version 1.3.6 ]**<br>- Fixed JSON Find Next to cycle global value matches across categories and include.<br>- Updated JSON Find Next to collapse the previous top-level category. |

| <img align="left" alt="VERIFICATION SUITE" src="https://img.shields.io/badge/VERIFICATION%20SUITE-0F172A?style=for-the-badge&labelColor=0F172A"> |
|---|
| - `pytest`: regression tests<br>- `ruff`: quality lint checks<br>- `semgrep`: static security analysis<br>- `trufflehog`: secret scanning<br>- `bandit`: Python security scan<br>- `pip-audit`: dependency vulnerability scan<br>- `Microsoft Defender CLI`: preflight for release artifacts<br>- `VirusTotal`: release evidence (hash-first with upload fallback)<br>- Published `SHA256` checksum + `security-report.txt` release artifact evidence<br><br>We run these checks to reduce risk, but false positive reports could still happen. |

| <img align="left" alt="LICENSE" src="https://img.shields.io/badge/LICENSE-MIT-8B0000?style=for-the-badge&labelColor=0F172A"> |
|---|
| MIT License. Copyright (c) 2026 Siindbad. |



