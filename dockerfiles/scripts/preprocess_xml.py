# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Preprocesses XML files to handle <include> directives."""

import argparse
import os
import sys
import traceback
from xml.dom import minidom
import xml.etree.ElementTree as ET


# Add the root of the repo to sys.path so we can import servo
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# pylint: disable=wrong-import-position
from servo.common.config import config_resolver


# pylint: enable=wrong-import-position


def parse_args(args):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file", help="Path to the input XML file")
    parser.add_argument("output_file", help="Path to the output XML file")
    return parser.parse_args(args)


def prettify(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, "utf-8")
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")
    # Remove extra blank lines
    return os.linesep.join([s for s in pretty_xml.splitlines() if s.strip()])


def process_include(element, base_path, loaded_files=None):
    """Recursively process include directives."""
    if loaded_files is None:
        loaded_files = set()

    for child in list(element):
        if child.tag == "include":
            name_tag = child.find("name")
            if name_tag is None or not name_tag.text:
                print(
                    f"Warning: <include> tag without <name> child found in {base_path}",
                    file=sys.stderr,
                )
                continue
            href = name_tag.text.strip()

            include_path = os.path.join(base_path, href)
            if not os.path.exists(include_path):
                # Try in servo/data if not found relative to base_path
                default_path = os.path.join(
                    os.path.dirname(__file__), "..", "..", "data", href
                )
                if os.path.exists(default_path):
                    include_path = default_path
                else:
                    print(
                        f"Error: Included file not found: {include_path}",
                        file=sys.stderr,
                    )
                    sys.exit(1)

            # Resolve to absolute path to avoid duplicate includes via
            # different relative paths
            include_path = os.path.abspath(include_path)

            index = list(element).index(child)
            element.remove(child)

            if include_path in loaded_files:
                continue

            loaded_files.add(include_path)

            try:
                include_tree = ET.parse(include_path)
                include_root = include_tree.getroot()
                # Recursively process includes in the included file
                process_include(
                    include_root, os.path.dirname(include_path), loaded_files
                )

                # Replace the <include> tag with the content of the included file
                for i, sub_element in enumerate(include_root):
                    element.insert(index + i, sub_element)

            except ET.ParseError as e:
                print(
                    f"Error parsing included file {include_path}: {e}", file=sys.stderr
                )
                sys.exit(1)
        else:
            # Recursively process children
            process_include(child, base_path, loaded_files)


def resolve_clobbers(root):
    """Resolve clobber_ok attributes and return a new resolved root."""
    resolver = config_resolver.ConfigResolver()
    # To keep track of original elements for content tags
    content_tags = {}  # (tag, name) -> [content_elements]

    for tag in [config_resolver.MAP_TAG, config_resolver.CONTROL_TAG]:
        for element in root.findall(tag):
            name_elem = element.find("name")
            if name_elem is None or not name_elem.text:
                continue
            name = name_elem.text.strip()
            doc = element.findtext("doc", default="undocumented")
            doc = " ".join(doc.split())
            alias = element.findtext("alias")
            params_elements = element.findall("params")
            params_list = [p.attrib.copy() for p in params_elements]

            # Save content tags if they exist
            for p in params_elements:
                content = p.find("content")
                if content is not None:
                    # We store it by (tag, name, cmd) if possible
                    cmd = p.attrib.get("cmd", "both")
                    content_tags[(tag, name, cmd)] = content

            try:
                resolver.add_entity(tag, name, doc, alias, params_list)
            except config_resolver.ConfigError as e:
                print(f"Error resolving {tag} {name}: {e}", file=sys.stderr)
                # SystemConfig raises error, so we should probably exit to be
                # consistent.
                sys.exit(1)

    new_root = ET.Element("root")
    # First maps, then controls
    for tag in [config_resolver.MAP_TAG, config_resolver.CONTROL_TAG]:
        # Only iterate over primary names, not aliases
        primary_names = sorted(
            [n for n in resolver.syscfg_dict[tag] if n not in resolver.aliases]
        )
        for name in primary_names:
            entry = resolver.syscfg_dict[tag][name]
            elem = ET.SubElement(new_root, tag)
            ET.SubElement(elem, "name").text = name
            if entry.get("doc") and entry["doc"] != "undocumented":
                ET.SubElement(elem, "doc").text = entry["doc"]

            # Add aliases back
            aliases = [a for a, r in resolver.aliases.items() if r == name]
            if aliases:
                ET.SubElement(elem, "alias").text = ",".join(sorted(aliases))

            if tag == config_resolver.MAP_TAG:
                params_list = [entry["map_params"]]
            else:
                params_list = []
                # Check if get and set are the same or different
                if entry["get_params"] == entry["set_params"]:
                    params_list = [entry["get_params"]]
                else:
                    # If they are different, we might have one being undefined
                    if entry["get_params"].get("drv") != "undefined":
                        params_list.append(entry["get_params"])
                    if entry["set_params"].get("drv") != "undefined":
                        params_list.append(entry["set_params"])

            for p_dict in params_list:
                p_elem = ET.SubElement(elem, "params")
                for k, v in sorted(p_dict.items()):
                    if k == "cmd" and len(params_list) == 1:
                        # If only one params, and it was inferred same for both,
                        # we don't need cmd="get" or cmd="set"
                        continue
                    p_elem.set(k, str(v))

                # Restore content if it was there
                cmd = p_dict.get("cmd", "both")
                content = content_tags.get((tag, name, cmd))
                if content is None and len(params_list) == 1:
                    # try "both" or one of them
                    content = content_tags.get((tag, name, "get")) or content_tags.get(
                        (tag, name, "set")
                    )

                if content is not None:
                    p_elem.append(content)

    return new_root


def main(argv):
    """Main function."""
    args = parse_args(argv)

    input_file = args.input_file
    output_file = args.output_file

    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    try:
        tree = ET.parse(input_file)
        root = tree.getroot()
        base_path = os.path.dirname(input_file)
        process_include(root, base_path)

        # Resolve clobbers to produce a clean flattened XML
        resolved_root = resolve_clobbers(root)

        pretty_xml = prettify(resolved_root)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(pretty_xml)

        print(f"Successfully processed {input_file} to {output_file}")

    except ET.ParseError as e:
        print(f"Error parsing input file {input_file}: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        traceback.print_exc()
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
