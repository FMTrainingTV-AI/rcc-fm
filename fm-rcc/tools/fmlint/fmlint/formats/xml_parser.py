"""XML format parser for fmxmlsnippet files."""

import xml.etree.ElementTree as ET
from typing import Optional


class XmlParseResult:
    """Result of parsing an fmxmlsnippet XML string or file."""

    def __init__(self):
        self.root = None           # ET.Element root
        self.steps = []            # list of ET.Element <Step> nodes
        self.parse_error = None    # str if XML is malformed
        self.raw_content = ""

    @property
    def ok(self) -> bool:
        return self.parse_error is None


def parse_xml_string(content: str) -> XmlParseResult:
    """Parse fmxmlsnippet XML from a string."""
    result = XmlParseResult()
    result.raw_content = content
    try:
        root = ET.fromstring(content)
        result.root = root
        result.steps = root.findall(".//Step")
    except ET.ParseError as e:
        result.parse_error = str(e)
    return result


def parse_xml_file(filepath: str) -> XmlParseResult:
    """Parse fmxmlsnippet XML from a file."""
    result = XmlParseResult()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            result.raw_content = f.read()
        tree = ET.parse(filepath)
        root = tree.getroot()
        result.root = root
        result.steps = root.findall(".//Step")
    except ET.ParseError as e:
        result.parse_error = str(e)
    except OSError as e:
        result.parse_error = str(e)
    return result


def cdata_texts(step) -> list:
    """Extract all Calculation CDATA text from a step element."""
    texts = []
    for calc in step.iter("Calculation"):
        if calc.text:
            texts.append(calc.text)
    return texts


def step_name(step) -> str:
    """Get the name attribute of a Step element."""
    return step.get("name", "")


def step_number(index: int) -> int:
    """Convert 0-based index to 1-based step number."""
    return index + 1
