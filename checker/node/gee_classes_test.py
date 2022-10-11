"""Tests for gee_classes."""

import pathlib
from typing import Any

from checker import stac
from checker.node import gee_classes
import unittest

Check = gee_classes.Check

COLLECTION = stac.StacType.COLLECTION
IMAGE = stac.GeeType.IMAGE

ID = 'a/collection'
FILE_PATH = pathlib.Path('test/path/should/be/ignored')


def make_node(classes: list[dict[str, Any]]) -> stac.Node:
  stac_data = {
      'summaries': {
          'eo:bands': [{
              'name': 'band_name',
              'description': 'a descr',
              'gee:classes': classes}]}}
  return stac.Node(ID, FILE_PATH, COLLECTION, IMAGE, stac_data)


class GeeClassesTest(unittest.TestCase):

  def test_valid(self):
    classes = [{'color': 'FAFAFA', 'description': 'A', 'value': 1},
               {'color': 'violet', 'description': 'B', 'value': 2}]
    issues = list(Check.run(make_node(classes)))
    self.assertEqual(0, len(issues))

  def test_valid_2(self):
    classes = [{'color': 'AABBCCDD', 'description': 'A', 'value': -1},
               {'color': 'white', 'description': 'B', 'value': 0}]
    issues = list(Check.run(make_node(classes)))
    self.assertEqual(0, len(issues))

  def test_bad_classes_must_be_a_list(self):
    stac_data = {
        'summaries': {
            'eo:bands': [{
                'name': 'band_name',
                'description': 'a descr',
                'gee:classes': 'not a list'}]}}
    node = stac.Node(ID, FILE_PATH, COLLECTION, IMAGE, stac_data)
    issues = list(Check.run(node))
    expect = [Check.new_issue(node, '"gee:classes" must be a list')]
    self.assertEqual(expect, issues)

  # TODO(schwehr): Test exception for just one class.

  def test_bad_only_one_class(self):
    node = make_node([{'color': 'red', 'description': 'A', 'value': 1}])
    issues = list(Check.run(node))
    expect = [Check.new_issue(
        node, '"gee:classes" must have at least 2 classes')]
    self.assertEqual(expect, issues)

  def test_bad_too_many_classes(self):
    def color(value: int) -> str:
      if value < 256:
        return f'{value:02x}0001'
      else:
        return f'00{value:02x}02'
    classes = [
        {'color': color(x), 'description': str(x), 'value': x}
        for x in range(256)]
    node = make_node(classes)
    issues = list(Check.run(node))
    expect = [Check.new_issue(
        node, '"gee:classes" has too many classes: 256')]
    self.assertEqual(expect, issues)

  def test_bad_classes_item_must_be_a_dict(self):
    stac_data = {
        'summaries': {
            'eo:bands': [{
                'name': 'band_name',
                'description': 'a descr',
                'gee:classes': [
                    'not a dict',
                    {'color': 'violet', 'description': 'B', 'value': 2}]}]}}
    node = stac.Node(ID, FILE_PATH, COLLECTION, IMAGE, stac_data)
    issues = list(Check.run(node))
    expect = [Check.new_issue(node, '"gee:classes" item must be a dict')]
    self.assertEqual(expect, issues)

  def test_bad_extra_key(self):
    node = make_node([
        {'color': 'red', 'description': 'A', 'value': 1, 'bad': 3},
        {'color': 'blue', 'description': 'B', 'value': 2}])
    issues = list(Check.run(node))
    expect = [Check.new_issue(node, 'Unexpected key: "bad"')]
    self.assertEqual(expect, issues)

  def test_bad_extra_keys(self):
    node = make_node([
        {'color': 'red', 'description': 'A', 'value': 1, 'bad1': 3, 'bad2': 4},
        {'color': 'blue', 'description': 'B', 'value': 2}])
    issues = list(Check.run(node))
    expect = [Check.new_issue(node, 'Unexpected keys: [\'bad1\', \'bad2\']')]
    self.assertEqual(expect, issues)

  def test_bad_value_is_str(self):
    node = make_node([
        {'color': 'red', 'description': 'A', 'value': 1},
        {'color': 'blue', 'description': 'B', 'value': 'a str'}])
    issues = list(Check.run(node))
    expect = [Check.new_issue(node, 'value must be a number: "a str"')]
    self.assertEqual(expect, issues)

  def test_bad_value_is_float(self):
    node = make_node([
        {'color': 'red', 'description': 'A', 'value': 1},
        {'color': 'blue', 'description': 'B', 'value': 3.14}])
    issues = list(Check.run(node))
    expect = [Check.new_issue(node, 'value must be a number: "3.14"')]
    self.assertEqual(expect, issues)

  def test_bad_description_not_str(self):
    node = make_node([
        {'color': 'red', 'description': 3, 'value': 1},
        {'color': 'blue', 'description': 'B', 'value': 2}])
    issues = list(Check.run(node))
    expect = [Check.new_issue(node, 'description must be a str: 3')]
    self.assertEqual(expect, issues)

  def test_bad_description_empty_str(self):
    node = make_node([
        {'color': 'red', 'description': '', 'value': 1},
        {'color': 'blue', 'description': 'B', 'value': 2}])
    issues = list(Check.run(node))
    expect = [Check.new_issue(node, 'Invalid description: ""')]
    self.assertEqual(expect, issues)

  def test_bad_description_too_long(self):
    node = make_node([
        {'color': 'red', 'description': 'A' * 1001, 'value': 1},
        {'color': 'blue', 'description': 'B', 'value': 2}])
    issues = list(Check.run(node))
    expect = [Check.new_issue(node, 'description too long: 1001')]
    self.assertEqual(expect, issues)

  def test_bad_color_is_number(self):
    node = make_node([
        {'color': 1, 'description': 'A', 'value': 1},
        {'color': 'blue', 'description': 'B', 'value': 2}])
    issues = list(Check.run(node))
    expect = [Check.new_issue(node, 'color must be a str: 1')]
    self.assertEqual(expect, issues)

  def test_bad_color_is_nonsense(self):
    node = make_node([
        {'color': 'nonsense', 'description': 'A', 'value': 1},
        {'color': 'blue', 'description': 'B', 'value': 2}])
    issues = list(Check.run(node))
    message = (
        'color must be a 6 (or 8) character hex or color name - '
        'found "nonsense"')
    expect = [Check.new_issue(node, message)]
    self.assertEqual(expect, issues)

  def test_bad_duplicate_values(self):
    node = make_node([
        {'color': 'red', 'description': 'A', 'value': 3},
        {'color': 'blue', 'description': 'B', 'value': 3}])
    issues = list(Check.run(node))
    expect = [Check.new_issue(node, 'values have duplicates')]
    self.assertEqual(expect, issues)

  def test_bad_unsorted_values(self):
    node = make_node([
        {'color': 'red', 'description': 'A', 'value': 5},
        {'color': 'blue', 'description': 'B', 'value': 4}])
    issues = list(Check.run(node))
    expect = [Check.new_issue(node, 'values must be sorted')]
    self.assertEqual(expect, issues)

  def test_bad_duplicate_descriptions(self):
    node = make_node([
        {'color': 'red', 'description': 'C', 'value': 1},
        {'color': 'blue', 'description': 'C', 'value': 2}])
    issues = list(Check.run(node))
    expect = [Check.new_issue(node, 'descriptions have duplicates')]
    self.assertEqual(expect, issues)

  def test_bad_duplicate_colors(self):
    node = make_node([
        {'color': 'green', 'description': 'D', 'value': 1},
        {'color': 'green', 'description': 'E', 'value': 2}])
    issues = list(Check.run(node))
    expect = [Check.new_issue(node, 'colors have duplicates')]
    self.assertEqual(expect, issues)

if __name__ == '__main__':
  unittest.main()
