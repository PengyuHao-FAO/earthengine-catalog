"""Check gee:classes.

See also bands.py

a.k.a. Categorical values in the old proto system

https://github.com/stac-extensions/classification
classification:classes
  Field Name  Type       Description
  value       integer    REQUIRED. Value of the class
  description string     Description of the class.
  name        string     REQUIRED. Short name of the class
  color_hint  RGB string Color for rendering (Hex RGB code in upper w/o #)
  nodata      boolean    Set to true if a no-data value, defaults to false

TODO(schwehr): Questions:
- Should the description end in a period or not?
- name, description, value - what order?

"summaries": {
      "eo:bands": [
         {
            "description": "Water classification",
            "gee:classes": [
               {
                  "color": "FAFAFA",
                  "description": "Land",
                  "value": 1
               },
               {
                  "color": "00C5FF",
                  "description": "Water",
                  "value": 2
               },
            ],
            "name": "water"
         }
      ],

TODO(schwehr): Make the hex all lower or upper case.  Just pick one.
"""

import re
from typing import Iterator

from checker import stac

SUMMARIES = 'summaries'
EO_BANDS = 'eo:bands'

CLASSES = 'gee:classes'

VALUE = 'value'
DESCRIPTION = 'description'
COLOR = 'color'

REQUIRED = frozenset({DESCRIPTION, VALUE})
FIELDS = frozenset({COLOR, DESCRIPTION, VALUE})

# TODO(schwehr): Factor out a complete ist of the colors.  It's needed
# for visualizations too.
COLOR_NAMES = frozenset({
    'black',
    'blue',
    'brown',
    'darkblue',
    'darkorange',
    'darkred',
    'darkslategray',
    'darkviolet',
    'ghostwhite',
    'green',
    'orange',
    'purple',
    'red',
    'slategray',
    'violet',
    'white',
    'yellow',
})

# Exceptions for things with one class.
ONE_CLASS = frozenset({
    'LANDSAT/MANGROVE_FORESTS',
    'UMD/GLAD/PRIMARY_HUMID_TROPICAL_FORESTS/v1',
})
# Exceptions for things that have duplicate descriptions.
DUPLICATE_DESCRIPTIONS = frozenset({
    'LANDFIRE/Vegetation/BPS/v1_4_0',
    'LANDFIRE/Vegetation/ESP/v1_2_0/AK',
    'LANDFIRE/Vegetation/ESP/v1_2_0/HI',
    'LANDFIRE/Vegetation/EVC/v1_4_0',
    'LANDFIRE/Vegetation/EVT/v1_4_0',
    'USDA/NASS/CDL'
})
# Exceptions for things where multiple catagories are the same color.
DUPLICATE_COLORS = frozenset({
    'AAFC/ACI',
    'CSP/ERGo/1_0/US/lithology',
    'ISDASOIL/Africa/v1/fcc',
    'JRC/D5/EUCROPMAP/V1',
    'LANDFIRE/Vegetation/BPS/v1_4_0',
    'LANDFIRE/Vegetation/ESP/v1_2_0/AK',
    'LANDFIRE/Vegetation/ESP/v1_2_0/CONUS',
    'LANDFIRE/Vegetation/ESP/v1_2_0/HI',
    'LANDFIRE/Vegetation/EVC/v1_4_0',
    'LANDFIRE/Vegetation/EVT/v1_4_0',
    'NOAA/CDR/PATMOSX/V53',
    'OpenLandMap/SOL/SOL_GRTGROUP_USDA-SOILTAX_C/v01',
    'Oxford/MAP/IGBP_Fractional_Landcover_5km_Annual',
    'Tsinghua/FROM-GLC/GAIA/v10',
    'USDA/NASS/CDL',
    'USGS/NLCD',
    'USGS/GAP/CONUS/2011',
    'USGS/NLCD_RELEASES/2016_REL',
})


class Check(stac.NodeCheck):
  """Checks gee:classes."""
  name = 'gee_classes'

  @classmethod
  def run(cls, node: stac.Node) -> Iterator[stac.Issue]:
    if SUMMARIES not in node.stac: return
    summaries = node.stac[SUMMARIES]
    if not isinstance(summaries, dict): return
    if EO_BANDS not in summaries: return
    bands = summaries[EO_BANDS]

    for band in bands:
      if CLASSES not in band: continue
      classes = band[CLASSES]
      if not isinstance(classes, list):
        yield cls.new_issue(node, f'"{CLASSES}" must be a list')
        continue
      if len(classes) < 2:
        if node.id not in ONE_CLASS:
          yield cls.new_issue(node, f'"{CLASSES}" must have at least 2 classes')
        if not classes: continue
      if len(classes) > 255:
        if 'LANDFIRE' not in node.id and 'USGS/GAP' not in node.id:
          yield cls.new_issue(
              node, f'"{CLASSES}" has too many classes: {len(classes)}')

      values = []
      descriptions = []
      colors = []
      for a_class in classes:
        if not isinstance(a_class, dict):
          yield cls.new_issue(node, f'"{CLASSES}" item must be a dict')
          continue

        keys = set(a_class)
        if not REQUIRED.issubset(keys):
          missing = list(REQUIRED.difference(keys))
          yield cls.new_issue(
              node, f'A {CLASSES} entry missing {missing})')

        extra_keys = list(keys.difference(FIELDS))
        if len(extra_keys) == 1:
          yield cls.new_issue(node, f'Unexpected key: "{extra_keys[0]}"')
        elif len(extra_keys) > 1:
          yield cls.new_issue(node, f'Unexpected keys: {sorted(extra_keys)}')

        if VALUE in a_class:
          value = a_class[VALUE]
          # TODO(schwehr): Can it be a float?
          if not isinstance(value, int):
            yield cls.new_issue(node, f'{VALUE} must be a number: "{value}"')
          else:
            values.append(value)
            # TODO(schwehr): Is there a way to constrain the value?

        if DESCRIPTION in a_class:
          description = a_class[DESCRIPTION]
          if not isinstance(description, str):
            yield cls.new_issue(
                node, f'{DESCRIPTION} must be a str: {description}')
          else:
            descriptions.append(description)
            # TODO(schwehr): Validate with `if not re.fullmatch`
            if len(description) < 1:
              yield cls.new_issue(
                  node, f'Invalid {DESCRIPTION}: "{description}"')
            elif len(description) > 1000:
              yield cls.new_issue(
                  node, f'{DESCRIPTION} too long: {len(description)}')

        if COLOR in a_class:
          color = a_class[COLOR]
          if not isinstance(color, str):
            yield cls.new_issue(
                node, f'{COLOR} must be a str: {color}')
          else:
            colors.append(color)
            if not re.fullmatch(r'[0-9a-fA-F]{6}([0-9a-fA-F]{2})?', color):
              if color not in COLOR_NAMES:
                yield cls.new_issue(
                    node,
                    f'{COLOR} must be a 6 (or 8) character hex or ' +
                    f'color name - found "{color}"')

      if len(values) != len(set(values)):
        # TODO(schwehr): List duplicates
        yield cls.new_issue(node, f'{VALUE}s have duplicates')

      if values != sorted(values):
        yield cls.new_issue(node, f'{VALUE}s must be sorted')

      if len(descriptions) != len(set(descriptions)):
        if node.id not in DUPLICATE_DESCRIPTIONS:
          # TODO(schwehr): List duplicates
          yield cls.new_issue(node, f'{DESCRIPTION}s have duplicates')

      if len(colors) != len(set(colors)):
        if node.id not in DUPLICATE_COLORS:
          # TODO(schwehr): List duplicates
          yield cls.new_issue(node, f'{COLOR}s have duplicates')
