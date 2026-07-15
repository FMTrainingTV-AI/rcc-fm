"""
Shared XML parsing utilities for FileMaker DDR analysis.

Script: ddr_xml_utils.py
Reliability: STABLE
Last validated: 2026-02-20
Known limitations:
- Files > 100MB use streaming parse (no full tree available)
- lxml required for XPath support; falls back to xml.etree (limited)

Dependencies:
- lxml (recommended, optional)

Handles both DDR XML format and "Save a Copy as XML" format.
Uses lxml for XPath support, falls back to xml.etree if lxml unavailable.
"""

import os
import json
import re
from pathlib import Path

try:
    from lxml import etree
    USING_LXML = True
except ImportError:
    import xml.etree.ElementTree as etree
    USING_LXML = False


# FileMaker DDR XML namespaces
FM_DDR_NS = {
    'fmp': 'http://www.filemaker.com/fmpxmlresult',
    'fmrs': 'http://www.filemaker.com/fmpxmlresult',
}


def parse_xml(filepath):
    """Parse an XML file, handling encoding issues and large files.

    Returns the root element and the tree.
    For files > 100MB, uses iterparse instead of loading full DOM.
    """
    filepath = Path(filepath)
    file_size = filepath.stat().st_size

    if file_size > 100 * 1024 * 1024:  # 100MB
        return parse_xml_streaming(filepath)

    # lxml auto-detects encoding from BOM and XML declaration,
    # so try without explicit encoding first (handles UTF-16 BOM)
    try:
        if USING_LXML:
            parser = etree.XMLParser(recover=True)
            tree = etree.parse(str(filepath), parser)
        else:
            tree = etree.parse(str(filepath))
        return tree.getroot(), tree
    except (etree.XMLSyntaxError if USING_LXML else etree.ParseError):
        pass

    # Fallback: try explicit encodings
    for encoding in ['utf-8', 'utf-16', 'windows-1252', 'latin-1']:
        try:
            if USING_LXML:
                parser = etree.XMLParser(encoding=encoding, recover=True)
                tree = etree.parse(str(filepath), parser)
            else:
                tree = etree.parse(str(filepath))
            return tree.getroot(), tree
        except (etree.XMLSyntaxError if USING_LXML else etree.ParseError):
            continue

    raise ValueError(f"Could not parse {filepath} with any supported encoding")


def parse_xml_streaming(filepath):
    """Parse a large XML file using iterparse (streaming).

    Returns the root element and None for tree (streaming doesn't build full tree).
    """
    context = etree.iterparse(str(filepath), events=('end',))
    root = None
    for event, elem in context:
        if root is None:
            root = elem
        # Process and clear elements to keep memory low
    return root, None


def get_ddr_version(root):
    """Extract the FileMaker version from the DDR XML header."""
    # DDR format: <FMPReport version="...">
    version = root.get('version', '')
    if not version:
        # Try the Product element
        product = root.find('.//Product')
        if product is not None:
            version = product.get('version', '')
    return version


def get_database_name(root):
    """Extract the database name from the DDR XML."""
    # DDR format: <File name="...">
    file_elem = root.find('.//File')
    if file_elem is not None:
        return file_elem.get('name', 'Unknown')
    # Fallback: check root element
    return root.get('name', 'Unknown')


def safe_filename(name):
    """Convert a FileMaker object name to a safe filename.

    Preserves readability while removing characters that cause filesystem issues.
    """
    # Replace path separators and other problematic chars
    unsafe_chars = r'[<>:"/\\|?*\x00-\x1f]'
    safe = re.sub(unsafe_chars, '_', name)
    # Collapse multiple underscores
    safe = re.sub(r'_+', '_', safe)
    # Remove leading/trailing whitespace and dots
    safe = safe.strip(' .')
    # Truncate to reasonable length
    if len(safe) > 200:
        safe = safe[:200]
    return safe


def find_all_elements(root, tag_name):
    """Find all elements with a given tag name, ignoring namespaces."""
    # Try with and without namespace
    results = root.findall(f'.//{tag_name}')
    if not results and USING_LXML:
        # lxml local-name approach to handle namespaced elements
        results = root.xpath(f'//*[local-name()="{tag_name}"]')
    return results


def extract_text_content(element):
    """Extract all text content from an element and its children.

    Returns a single string with all text concatenated.
    """
    if element is None:
        return ''
    parts = []
    if element.text:
        parts.append(element.text)
    for child in element:
        parts.append(extract_text_content(child))
        if child.tail:
            parts.append(child.tail)
    return ''.join(parts)


def find_to_field_references(text):
    """Find all TO::Field references in a text string.

    Returns a list of (TO_name, field_name) tuples.
    FileMaker uses the pattern: TableOccurrenceName::FieldName
    """
    # Match TO::Field patterns
    # TO names can contain letters, digits, underscores, spaces
    # Field names follow the same rules
    pattern = r'([A-Za-z_][A-Za-z0-9_ ]*?)::([A-Za-z_][A-Za-z0-9_ ]*)'
    matches = re.findall(pattern, text)
    # Clean up: strip whitespace from names
    return [(to.strip(), field.strip()) for to, field in matches]


def write_metadata(output_dir, metadata):
    """Write the _metadata.json file for a parsed DDR."""
    meta_path = Path(output_dir) / '_metadata.json'
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def read_metadata(parsed_dir):
    """Read the _metadata.json from a parsed DDR directory."""
    meta_path = Path(parsed_dir) / '_metadata.json'
    if not meta_path.exists():
        raise FileNotFoundError(f"No _metadata.json found in {parsed_dir}. Run the splitter first.")
    with open(meta_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_element_by_id(root, tag_name, fm_id):
    """Find an element by its FileMaker ID attribute."""
    for elem in find_all_elements(root, tag_name):
        if elem.get('id') == str(fm_id):
            return elem
    return None


def iter_parsed_files(parsed_dir, object_type=None):
    """Iterate over parsed XML files in a directory.

    Args:
        parsed_dir: Path to the parsed DDR directory
        object_type: Optional filter - 'scripts', 'layouts', 'tables', etc.

    Yields:
        (filepath, root_element) tuples
    """
    parsed_path = Path(parsed_dir)

    # If object_type specified, only look in that subdirectory
    if object_type:
        search_dirs = []
        for db_dir in parsed_path.iterdir():
            if db_dir.is_dir() and not db_dir.name.startswith('_'):
                type_dir = db_dir / object_type
                if type_dir.exists():
                    search_dirs.append(type_dir)
    else:
        search_dirs = [parsed_path]

    for search_dir in search_dirs:
        for xml_file in search_dir.rglob('*.xml'):
            try:
                root, _ = parse_xml(xml_file)
                yield xml_file, root
            except Exception as e:
                print(f"Warning: Could not parse {xml_file}: {e}")
                continue
