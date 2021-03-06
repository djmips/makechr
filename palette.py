import errors
import string


class Palette(object):
  def __init__(self):
    self.bg_color = None
    self.pals = []
    self.pal_as_sets = []

  def __str__(self):
    return ('P/' +
            '/'.join(['-'.join(['%02x' % c for c in row]) for row in self.pals])
            + '/')

  def set_bg_color(self, bg_color):
    self.bg_color = bg_color

  def add(self, p):
    if not self.bg_color in p:
      raise errors.PaletteBgcolorError(self.bg_color, p)
    p = [self.bg_color] + [c for c in p if c != self.bg_color]
    self.pals.append(p)
    self.pal_as_sets.append(set(p))

  def select(self, color_needs):
    want = set([c for c in color_needs if not c is None])
    for i,p in enumerate(self.pal_as_sets):
      if want <= p:
        break
    else:
      raise IndexError
    return (i, self.pals[i])

  def get(self, i):
    if i < len(self.pals):
      return self.pals[i]


class PaletteParser(object):
  def parse(self, text):
    self.i = 0
    self.text = text
    self.fetch_literal('P') or self.die('Expected: "P"')
    self.fetch_literal('/') or self.die('Expected: "/"')
    pal = Palette()
    for n in xrange(4):
      row = []
      val = self.fetch_hex()
      if not val:
        break
      row.append(val)
      pal.set_bg_color(val)
      for q in xrange(3):
        if not self.fetch_literal('-'):
          break
        val = self.fetch_hex()
        if not val:
          self.die('Invalid hex value')
        row.append(val)
      self.fetch_literal('/') or self.die('Expected: "/"')
      pal.add(row)
    self.fetch_done() or self.die('Expected: end of input')
    return pal

  def fetch_literal(self, want):
    if self.i >= len(self.text):
      return False
    if self.text[self.i] == want:
      self.i += 1
      return True
    return False

  def fetch_hex(self):
    if self.i + 1 >= len(self.text):
      return None
    if not self.text[self.i] in string.hexdigits:
      return None
    if not self.text[self.i + 1] in string.hexdigits:
      return None
    val = int(self.text[self.i:self.i + 2], 16)
    self.i += 2
    return val

  def fetch_done(self):
    return self.i >= len(self.text)

  def die(self, msg):
    raise errors.PaletteParseError(self.text, self.i, msg)
