"""Checks file paths.

STAC Catalogs:
- The top level is catalog.json with an id of 'GEE_catalog'
- Datasets are under an organization directory with a catalog.json:
  ORG/catalog.json
- The `id` of the catalog is the same as the top level directory
- NASA, NOAA, and USGS are special in that they can have 2 levels of catalogs:
  - NASA/catalog.json
  - NASA/other_thing/catalog.json
- The `id` of 2-level catalogs is like 'NASA/other_thing'
- There cannot be more than two levels of catalogs

STAC Collections:
- A dataset with an `id` of ORG/b will have a STAC collection of ORG/ORG_b.json
- Datasets with deeper `id`'s clamp at one subdirectory.  e.g.
  ORG/b/c/d will have a file ORG/ORG_b_c_d.json
- NASA, NOAA, and USGS are special in that they can have 2 levels of collections
  - NASA/a -> NASA/NASA_a.json
  - NASA/b/c -> NASA/b/NASA_b_c.json
  - NASA/d/e/f/g -> NASA/d/NASA_d_e_f_g.json
- 'USGS/GFSAD1000' is a special case that violates the 2-level rules because it
  did that before the checks existed.
"""

import pathlib
from typing import Iterator

from checker import stac

GEE_CATALOG = 'GEE_catalog'
CATALOG_NAME = 'catalog.json'
GEE_CATALOG_PATH = pathlib.Path(CATALOG_NAME)


class Check(stac.NodeCheck):
  """Checks file paths."""
  name = 'file_path'

  @classmethod
  def run(cls, node: stac.Node) -> Iterator[stac.Issue]:
    id_field = node.id
    id_path = pathlib.Path(id_field)
    id_parts = id_path.parts

    if not id_parts:
      yield cls.new_issue(node, 'Empty id field')
      return

    if node.type == stac.StacType.CATALOG:
      # The top level catalog is special.
      if node.id == GEE_CATALOG:
        if node.path != GEE_CATALOG_PATH:
          yield cls.new_issue(node, f'"{GEE_CATALOG}" in the wrong place')
        return
      if node.path == GEE_CATALOG_PATH and node.id != GEE_CATALOG:
        yield cls.new_issue(node, f'Root must have an id of {GEE_CATALOG}')
        return

      # This may need to change if the catalog every starts having more than one
      # STAC Catalog per directory.
      if node.path.name != CATALOG_NAME:
        yield cls.new_issue(node, f'Catalog file must be {CATALOG_NAME}')
        return
      if len(id_parts) > 2:
        yield cls.new_issue(node, 'Catalog too deep')
        return

      if node.is_two_level():
        expected_path = pathlib.Path(*id_parts[:2]) / 'catalog.json'
        if node.path != expected_path:
          yield cls.new_issue(
              node,
              f'2-level expected path: {expected_path} found: {node.path}')
        return

      # Single level catalog
      if len(id_parts) != 1:
        # Not NASA, NOAA, or USGS
        yield cls.new_issue(node, f'expected length 1 path: {list(id_parts)}')
      else:
        expected_path = pathlib.Path(id_parts[0]) / 'catalog.json'
        if node.path != expected_path:
          yield cls.new_issue(
              node, f'expected path: {expected_path} found: {node.path}')

      return  # Done with catalog

    # Collection
    if node.is_two_level():
      if id_field.startswith('USGS/GFSAD1000'):
        # USGS/GFSAD1000_V1 -> USGS/GFSAD1000/USGS_GFSAD1000_V1.json
        prefix, version = id_field.split('_')
        parts = prefix.split('/')
        subdir = pathlib.Path(parts[0])
        subdir2 = pathlib.Path(parts[1])
        filename = '_'.join([parts[0], parts[1], version]) + '.json'
        expected_path = subdir / subdir2 /filename
        if node.path != expected_path:
          yield cls.new_issue(
              node,
              'Col USGS/GFSAD1000: expected path: ' +
              f'{expected_path} found: {node.path}')
        return
      if len(id_parts) == 2:
        assert False, 'Internal error - this is cannot be two level: ' + node.id
      else:
        subdir = pathlib.Path(id_parts[0])
        subdir2 = pathlib.Path(id_parts[1])

        filename = '_'.join(id_parts) + '.json'
        expected_path = subdir / subdir2 /filename
        if node.path != expected_path:
          yield cls.new_issue(
              node,
              f'Col 2-level: expected path: {expected_path} found: {node.path}')
    else:  # One level collection
      # Datasets ids starting with 'projects' loose their first directory part.
      expected_subdir = pathlib.Path(
          id_parts[1] if id_parts[0] == 'projects' else id_parts[0])

      expected_path = (
          pathlib.Path(expected_subdir) / (node.id.replace('/', '_') + '.json'))
      if expected_path != node.path:
        message = (
            f'Col: expected one level path: {expected_path} found: {node.path}')
        yield cls.new_issue(node, message)
