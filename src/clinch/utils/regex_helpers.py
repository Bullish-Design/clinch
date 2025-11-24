# src/clinch/utils/regex_helpers.py
from __future__ import annotations

ISO_DATETIME = r"""\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z"""
EMAIL = r"""[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"""
IPV4 = r"""(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)){3}"""
IPV6 = r"""(?:[0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4}"""
URL = r"""https?://[\w.-]+(?:/[\w./?%&=+#-]*)?"""
UUID = r"""[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89ABab][0-9a-fA-F]{3}-[0-9a-fA-F]{12}"""
SEMVER = r"""\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?(?:\+[A-Za-z0-9.-]+)?"""
HEX_COLOR = r"""#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})"""
FILE_PATH = r"""(?:/[^/\s]+)+/?"""
