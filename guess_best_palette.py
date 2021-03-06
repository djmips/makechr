import errors
import rgb
import palette
import partitions
from constants import *


class GuessBestPalette(object):

  # to_color_set
  #
  # Given a string, often from a hash table key, parse it to make a sorted
  # color set, without any None elements. The order is descending, making it
  # easy to do subset comparisions later.
  #
  # text: A text representation of a color set. Example: '[45, 15, 8, None]'
  def to_color_set(self, color_needs):
    return sorted([e for e in color_needs if not e is None], reverse=True)

  # is_color_subset
  #
  # Return whether subject is a strict subset of target.
  #
  # subject: A color set.
  # target: A color set.
  def is_color_subset(self, subject, target):
    return set(subject) <= set(target)

  # get_uniq_color_sets
  #
  # Given a color manifest, remove duplicates and sort.
  #
  # color_manifest: A dict of color sets.
  def get_uniq_color_sets(self, color_manifest):
    seen = {}
    for color_needs in color_manifest:
      color_set = self.to_color_set(color_needs)
      name = '-'.join(['%02x' % e for e in color_set])
      seen[name] = color_set
    return sorted(seen.values())

  def get_minimal_colors(self, uniq_color_sets):
    minimized = []
    for i, color_set in enumerate(uniq_color_sets):
      for j, target in enumerate(uniq_color_sets[i + 1:]):
        if self.is_color_subset(color_set, target):
          break
      else:
        minimized.append(color_set)
    return minimized

  def merge_color_sets(self, color_set_collection, merge_strategy):
    result = []
    for choices in merge_strategy:
      merged = set()
      for c in choices:
        merged |= set(color_set_collection[c])
      if len(merged) > PALETTE_SIZE:
        return None
      result.append(merged)
    return result

  # get_background_color
  #
  # Given a list of colors, return the best background color. Prefer
  # black if possible, otherwise, use the smallest numerical value.
  #
  # combined_colors: List of color needs.
  def get_background_color(self, combined_colors):
    possibilities = set(combined_colors[0])
    for color_set in combined_colors[1:]:
      possibilities = possibilities & set(color_set)
    if rgb.BLACK in possibilities:
      return rgb.BLACK
    if possibilities:
      return min(possibilities)
    return None

  # get_valid_combinations
  #
  # Some of the color_sets are finalized (full PaletteOptions) the others
  # remaining need to be merged. Try all possible combinations, and for each
  # one determine the background color. Return all possibilities, at least 1.
  #
  # finalized: Full color sets.
  # remaining: Color sets that need to be merged.
  def get_valid_combinations(self, finalized, remaining):
    merged_color_possibilities = []
    num_available = NUM_ALLOWED_PALETTES - len(finalized)
    for merge_strategy in partitions.partitions(len(remaining)):
      if len(merge_strategy) > num_available:
        continue
      merged_colors = self.merge_color_sets(remaining, merge_strategy)
      if not merged_colors:
        continue
      combined_colors = finalized + merged_colors
      bg_color = self.get_background_color(combined_colors)
      if bg_color is None:
        continue
      merged_color_possibilities.append([bg_color, combined_colors])
    if not len(merged_color_possibilities):
      raise errors.TooManyPalettesError(finalized, to_merge=remaining)
    return merged_color_possibilities

  def get_merged_color_possibilities(self, minimal_colors):
    finalized = []
    remaining = []
    # We know from earlier steps that minimal_colors is a set of color_sets
    # such that none are subsets of each other. However, some may have some
    # colors in common such that they could be merged. First, let's remove all
    # full palettes, leaving only those that might be mergable.
    for color_set in minimal_colors:
      if len(color_set) == PALETTE_SIZE:
        finalized.append(color_set)
      else:
        remaining.append(color_set)
    if remaining:
      # There are remaining unmerged palettes. Generate all valid combinations
      # of merged palettes, which may fail if there is no way to merge them.
      return self.get_valid_combinations(finalized, remaining)
    elif len(finalized) > NUM_ALLOWED_PALETTES:
      # The number of necessary palettes is more than the number allowed.
      raise errors.TooManyPalettesError(minimal_colors)
    else:
      # There is only one valid combination.
      bg_color = self.get_background_color(finalized)
      return [[bg_color, finalized]]

  # get_palette
  #
  # Given list of possible palettes, just pick and build the first one.
  #
  # possibilities: List of possible palettes, must have at least one element.
  def get_palette(self, possibilities):
    (bg_color, color_set_collection) = possibilities[0]
    pal = palette.Palette()
    pal.set_bg_color(bg_color)
    for color_set in color_set_collection:
      pal.add(color_set)
    return pal

  def make_palette(self, color_needs_list):
    uniq_color_sets = self.get_uniq_color_sets(color_needs_list)
    minimal_colors = self.get_minimal_colors(uniq_color_sets)
    possibilities = self.get_merged_color_possibilities(minimal_colors)
    return self.get_palette(possibilities)
