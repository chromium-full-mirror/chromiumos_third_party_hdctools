#!/usr/bin/env python3
# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Helper module to generate system control files."""

import argparse
import copy
import glob
import importlib.util
import json
import os
import re
import sys
import time


class ServoConfigGeneratorError(Exception):
  """Error class for INA control generation errors."""
  pass

class XMLElementGenerator:
  """Helper class to generate a formatted XML element.

  Attributes:
    _name: name of the element
    _text: text to go between opening and close brackets
    _attribute_string: string containing attributes and values for element
  """

  def __init__(self, name, text, attributes={}, attribute_order=[]):
    """Prepare substrings to make formatted XML element retrieval easier.

    Args:
      name: name of the element <[name]>.
      text: text to go between opening and closing tag.
      attributes: key/value pairs of attributes for the tag.
      attribute_order: order in which to print the attributes.
    """
    self._name = name
    self._text = text
    keys = [k for k in attribute_order if k in attributes]
    keys += list(set(attributes.keys()) - set(attribute_order))
    self._attribute_string = ''.join(' %s="%s"' %
                                     (k, attributes[k]) for k in keys)

  def GetXML(self):
    """Retrieves XML string for element.

    Returns:
      formatted string for the element.
    """
    output_format = '<%s%s>%s</%s>'
    return output_format % (self._name, self._attribute_string,
                            self._text, self._name)


class ServoControlGenerator:
  """Helper class to generate formatted XML for servo controls.

  Attributes:
    _ctrl_elements: list XMLElementGenerators to build control
                    element on retrieval.
  """

  # order of the attributes for the params element.
  params_attr_order = ['cmd', 'interface', 'drv', 'child',
                       'channel', 'type', 'subtype']

  def __init__(self, name, docstring, params, params2=None):
    """Init an XMLElementGenerator for each element.

    Prepare control XML retrieval by preparing XML generators for each
    component.

    Args:
      name: name tag for the control
      docstring: docstring for the control
      params: attributes for the params tag
      params2: attributes for the 2nd params tag
               (applicable for controls that have both set & get)

    Raises:
      ServoConfigGeneratorError if two malformatted params elements are
      provided.
    """
    parameters = [params]
    if params2:
      # checking to make sure that if there are two paramteter sets, one of them
      # is a set command and the other is a get command.
      if 'cmd' not in params or 'cmd' not in params2:
        raise ServoConfigGeneratorError('Control %s has 2 params. cmd attribute'
                                      ' is required for each param.' % name)
      cmds = set([params['cmd'], params2['cmd']])
      if cmds != set(['get', 'set']):
        raise ServoConfigGeneratorError("Control %s has 2 params, and cmd "
                                      "attributes are not 'set' and 'get'"
                                      % name)
      parameters.append(params2)

    self._ctrl_elements = [XMLElementGenerator('name', name),
                           XMLElementGenerator('doc', docstring)]
    for parameter in parameters:
      self._ctrl_elements.append(XMLElementGenerator('params', '',
                                                     parameter,
                                                     self.params_attr_order))

  def GetControlXML(self):
    """Retrieves XML string for a servod control.

    Returns:
      formatted string for the XML control.
    """
    # for each control element, generate the XML and join together into one
    # string.
    ctrl_text = ''.join(element.GetXML() for element in self._ctrl_elements)
    ctrl_element = XMLElementGenerator('control', ctrl_text, {})
    return ctrl_element.GetXML()


class ServoConfigFileGenerator:
  """Helper to generate XML servod configuration files.

  Attributes:
    _text: xml file as a string
  """

  XML_VERSION = '1.0'

  def __init__(self, ctrl_generators, includes=None, inline='',
               intro_comments=''):
    """Prepares entire XML file as a string for easier export later.

    Note: use inline carefully as it just gets appended verbatim to the end
    of the config file.

    Args:
      ctrl_generators: ServoControlGenerators for all ctrls in the config file
      inline: string to add verbatim to the config file
      includes: list of xml files to include
      intro_comments: comments to add in the beginning
    """
    self._text = '<?xml version="%s"?>' % self.XML_VERSION
    body = ''
    if intro_comments:
      body += '<!-- %s -->' % intro_comments
    if includes:
      for include in includes:
        name_element = XMLElementGenerator(name='name', text=include)
        include_tag = XMLElementGenerator(name='include',
                                          text=name_element.GetXML())
        body += include_tag.GetXML()
    if inline:
      body += inline
    for generator in ctrl_generators:
      body += generator.GetControlXML()
    file_as_element = XMLElementGenerator(name='root', text=body)
    self._text += file_as_element.GetXML()

    level = -1
    output = ''
    for i, c in enumerate(self._text):
      output += c
      try:
        if self._text[i:i+2] == '</':
          level -= 1
        elif self._text[i:i+3] == '><!':
          output += '\n' + '  ' * level
        elif self._text[i:i+3] == '></':
          output += '\n' + '  ' * level
        elif self._text[i:i+2] == '><':
          level += 1
          output += '\n' + '  ' * level
      except IndexError:
        pass
    self._text = output

  def WriteToFile(self, destination):
    """Helper to write to file.

    Args:
      destination: dest where to save the file.
    """
    with open(destination, 'w') as f:
      f.write(self._text)

  def GetAsString(self):
    """Get entire XML configuration file as a string.

    Returns:
      formatted string for the entire XML config file.
    """
    return self._text
