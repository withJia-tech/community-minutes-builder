# Third-party dependencies

This repository does not vendor the packages below. Versions installed in a
particular environment may vary within the supported bounds; consult the
actual installed packages for their full licence texts and notices.

| Component | Role | Licence / terms | Upstream |
|---|---|---|---|
| lxml | DOCX XML parsing | BSD-style | https://lxml.de/ |
| Pillow | Rendering/cropping embedded slide images | MIT-CMU (PIL-derived licence) | https://python-pillow.github.io/ |
| Poppler / `pdfinfo`, `pdftotext`, `pdftoppm` | PDF analysis and rendering | GPL-family licensing; see the installed distribution | https://poppler.freedesktop.org/ |
| pytest | Test runner, development only | MIT | https://pytest.org/ |
| python-docx | Word-compatible test fixture generation, development only | MIT | https://python-docx.readthedocs.io/ |
| Claude Code | Optional external plugin host, not bundled | Proprietary vendor terms | https://code.claude.com/ |

This summary is informational and not a substitute for examining the installed
components' NOTICE/COPYING files. Poppler executable use is external; no
Poppler source or binaries are redistributed by this project.
