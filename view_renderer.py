from PIL import Image, ImageDraw
from constants import *
import math
import os
import rgb


GRAY_COLOR = (64, 64, 64)
ERROR_GRID_COLOR  = (0xf0, 0x20, 0x20)
ERROR_GRID_COLOR2 = (0xf0, 0x80, 0x80)
GRAY_PALETTE = [225, 150, 75, 0]
SCALE_FACTOR = 2


class ViewRenderer(object):
  def __init__(self):
    self.img = None
    self.draw = None
    self.font = None

  def create_file(self, outfile, width, height, color=None):
    if color is None:
      color = GRAY_COLOR
    self.img = Image.new('RGB', (width, height), color)
    self.draw = ImageDraw.Draw(self.img)
    self.outfile = outfile

  def save_file(self):
    self.img.save(self.outfile)

  def to_tuple(self, value):
    r = value / (256 * 256)
    g = (value / 256) % 256
    b = value % 256
    return (r,g,b)

  def palette_option_to_colors(self, poption):
    return [self.to_tuple(rgb.RGB_COLORS[p]) for p in poption]

  def count_to_color(self, count):
    COLORS = [None,               # unused
              None,               # clear
              (0x00, 0x80, 0x00), # dark green
              (0x00, 0xff, 0x00), # light green
              (0x00, 0xff, 0xff), # light blue
              (0x00, 0x00, 0xff), # blue
              (0x80, 0x00, 0x80), # dark purple
              (0xff, 0x00, 0xff), # light purple
              (0xff, 0x40, 0x40), # red
              (0xff, 0x80, 0x00), # orange
              (0xff, 0xff, 0x00)] # yellow
    if count < len(COLORS):
      return COLORS[count]
    return (0xff, 0xff, 0xff)

  def resource(self, rel):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), rel)

  def load_nt_font(self):
    self.font = [None] * 16
    font_img = Image.open(self.resource('res/nt_font.png'))
    for n in range(16):
      self.font[n] = font_img.crop([n*7,0,n*7+7,11])
    font_img.close()

  def draw_block(self, block_y, block_x, poption):
    s = self.scale * 8
    i = block_y * 2 * s
    j = block_x * 2 * s
    # Borders for the individual colors in the palette block.
    # 0) Background color, fills entire block.
    # 1) Color 1, upper-right with a 1-pixel border, squatter than a square.
    # 2) Color 2, lower-left with a 1-pixel border, thinner than a square.
    # 3) Color 3, lower-right, true square.
    offsets = [[ 0, 0, s*2-1, s*2-1],
               [ s, 1, s*2-1,   s-1],
               [ 1, s,   s-1, s*2-1],
               [ s, s, s*2-1, s*2-1]]
    color = self.palette_option_to_colors(poption)
    for k, c in enumerate(color):
      f = offsets[k]
      self.draw.rectangle([j+f[0],i+f[1],j+f[2],i+f[3]], c)

  def draw_poption(self, n, poption):
    if not poption:
      return
    j = n * 5 * 8 + 8
    offsets = [[ 0, 8, 7,15],
               [ 8, 8,15,15],
               [16, 8,23,15],
               [24, 8,31,15]]
    color = self.palette_option_to_colors(poption)
    for k, c in enumerate(color):
      f = offsets[k]
      self.draw.rectangle([j+f[0],f[1],j+f[2],f[3]], c)

  def draw_chr(self, tile, tile_y, tile_x):
    s = self.scale * 8
    t = self.scale
    for y in xrange(8):
      for x in xrange(8):
        base_y = tile_y * (s + 1)
        base_x = tile_x * (s + 1)
        pixel = tile.get(y, x)
        gray = GRAY_PALETTE[pixel]
        self.draw.rectangle([base_x + x * t, base_y + y * t,
                             base_x + x * t + t - 1, base_y + y * t + t - 1],
                             (gray, gray, gray))

  def draw_square(self, tile_y, tile_x, count):
    s = self.scale * 8
    i = tile_y * s
    j = tile_x * s
    color = self.count_to_color(count)
    if not color:
      color = (0x00, 0x00, 0x00)
    self.draw.rectangle([j+0,i+0,j+s,i+s], color)

  def draw_empty_block(self, block_y, block_x):
    s = self.scale * 8
    i = block_y * 2 * s
    j = block_x * 2 * s
    self.draw.rectangle([j+0,i+0,j+s*2,i+s*2], (0,0,0,255))

  def draw_nt_value(self, tile_y, tile_x, nt):
    s = self.scale * 8
    upper = self.font[nt / 16]
    lower = self.font[nt % 16]
    # Left digit (upper nibble).
    self.img.paste(upper, [tile_x*s+1,tile_y*s+3,tile_x*s+8,tile_y*s+14])
    # Right digit (lower nibble).
    self.img.paste(lower, [tile_x*s+8,tile_y*s+3,tile_x*s+15,tile_y*s+14])

  def draw_error(self, y, x, sz):
    # Inner line.
    self.draw.line([   x,    y, x+sz,    y], ERROR_GRID_COLOR)
    self.draw.line([   x,    y,    x, y+sz], ERROR_GRID_COLOR)
    self.draw.line([   x, y+sz, x+sz, y+sz], ERROR_GRID_COLOR)
    self.draw.line([x+sz,    y, x+sz, y+sz], ERROR_GRID_COLOR)
    # Outer line.
    self.draw.line([   x-1,    y-1, x+sz+1,    y-1], ERROR_GRID_COLOR2)
    self.draw.line([   x-1,    y-1,    x-1, y+sz+1], ERROR_GRID_COLOR2)
    self.draw.line([   x-1, y+sz+1, x+sz+1, y+sz+1], ERROR_GRID_COLOR2)
    self.draw.line([x+sz+1,    y-1, x+sz+1, y+sz+1], ERROR_GRID_COLOR2)

  def is_empty_block(self, y, x, artifacts, cmanifest, bg):
    # TODO: This could be much more efficient. Perhaps add a value to artifacts
    # that determines whether the tile / block is empty.
    cid_0 = artifacts[y * 2  ][x * 2  ][ARTIFACT_CID]
    cid_1 = artifacts[y * 2  ][x * 2+1][ARTIFACT_CID]
    cid_2 = artifacts[y * 2+1][x * 2  ][ARTIFACT_CID]
    cid_3 = artifacts[y * 2+1][x * 2+1][ARTIFACT_CID]
    if cid_0 == cid_1 and cid_1 == cid_2 and cid_2 == cid_3:
      color_needs = cmanifest.get(cid_0)
      if color_needs == [bg, None, None, None]:
        return True
    return False

  def draw_grid(self, width, height):
    s = self.scale * 8
    tile_grid_color = (0x20,0x80,0x20)
    block_grid_color = (0x00,0xf0,0x00)
    # Draw tile grid.
    for col in xrange(16):
      self.draw.line([col*2*s+s, 0, col*2*s+s, height], tile_grid_color)
    for row in xrange(15):
      self.draw.line([0, row*2*s+s, width, row*2*s+s], tile_grid_color)
    # Draw block grid.
    for col in xrange(1, 16):
      self.draw.line([col*2*s, 0, col*2*s, height], block_grid_color)
    for row in xrange(1, 15):
      self.draw.line([0, row*2*s, width, row*2*s], block_grid_color)

  # create_colorization_view
  #
  # Create an image that shows which palette is used for each block.
  #
  # outfile: Filename to output the view to.
  # artifacts: Artifacts created by the image processor.
  # palette: The palette for the image.
  def create_colorization_view(self, outfile, artifacts, palette, cmanifest):
    self.scale = SCALE_FACTOR
    width, height = (256 * self.scale, 240 * self.scale)
    self.create_file(outfile, width, height)
    for y in xrange(NUM_BLOCKS_Y):
      for x in xrange(NUM_BLOCKS_X):
        pid = artifacts[y * 2][x * 2][ARTIFACT_PID]
        poption = palette.get(pid)
        if self.is_empty_block(y, x, artifacts, cmanifest, poption[0]):
          self.draw_empty_block(y, x)
          continue
        self.draw_block(y, x, poption)
    self.save_file()

  # create_resuse_view
  #
  # Create an image that shows which tiles are reused, color coded by how many
  # times they appear.
  #
  # outfile: Filename to output the view to.
  # artifacts: Artifacts created by the image processor.
  # nt_count: Dict mapping nametable values to number of times.
  def create_reuse_view(self, outfile, artifacts, nt_count):
    self.scale = SCALE_FACTOR
    width, height = (256 * self.scale, 240 * self.scale)
    self.create_file(outfile, width, height)
    for block_y in xrange(NUM_BLOCKS_Y):
      for block_x in xrange(NUM_BLOCKS_X):
        for i in range(2):
          for j in range(2):
            y = block_y * 2 + i
            x = block_x * 2 + j
            nt = artifacts[y][x][ARTIFACT_NT]
            self.draw_square(y, x, nt_count[nt])
    self.save_file()

  # create_palette_view
  #
  # Create an image that shows the palette.
  #
  # outfile: Filename to output the palette to.
  # palette: The palette to show.
  def create_palette_view(self, outfile, palette):
    self.create_file(outfile, 168, 24)
    for i in xrange(4):
      poption = palette.get(i)
      self.draw_poption(i, poption)
    self.save_file()

  # create_nametable_view
  #
  # Create an image that shows nametable values for each tile.
  #
  # outfile: Filename to output the view to.
  # artifacts: Artifacts created by the image processor.
  def create_nametable_view(self, outfile, artifacts):
    self.scale = SCALE_FACTOR
    width, height = (256 * self.scale, 240 * self.scale)
    self.load_nt_font()
    self.create_file(outfile, width, height, (255, 255, 255))
    for block_y in xrange(NUM_BLOCKS_Y):
      for block_x in xrange(NUM_BLOCKS_X):
        for i in range(2):
          for j in range(2):
            y = block_y * 2 + i
            x = block_x * 2 + j
            nt = artifacts[y][x][ARTIFACT_NT]
            if nt != 0:
              self.draw_nt_value(y, x, nt)
    self.draw_grid(width, height)
    self.save_file()

  # create_chr_view
  #
  # Create an image that shows chr tiles in a 16x16 grid layout. Has an
  # abnormal size, which is the size of a chr tile, times 16, plus a 1-pixel
  # border between each tile.
  #
  # outfile: Filename to output the view to.
  # chr_data: List of chr tiles.
  def create_chr_view(self, outfile, chr_data):
    self.scale = SCALE_FACTOR
    s = self.scale * 8
    rows = int(math.ceil(len(chr_data) / 16.0))
    width, height = (16 * (s + 1) - 1, rows * (s + 1) - 1)
    self.create_file(outfile, width, height, (255, 255, 255))
    for k, tile in enumerate(chr_data):
      tile_y = k / 16
      tile_x = k % 16
      self.draw_chr(tile, tile_y, tile_x)
    self.save_file()

  # create_error_view
  #
  # Create an image that shows the errors.
  #
  # outfile: Filename to output the error display to.
  # img: Input pixel art image.
  # errs: List of errors created by processor.
  def create_error_view(self, outfile, img, errs):
    self.scale = SCALE_FACTOR
    width, height = (256 * self.scale, 240 * self.scale)
    self.img = img.resize((width, height), Image.NEAREST).convert('RGB')
    self.draw = ImageDraw.Draw(self.img)
    self.outfile = outfile
    self.draw_grid(width, height)
    s = self.scale * 8
    # Draw errors.
    for e in errs:
      if getattr(e, 'tile_y', None) and getattr(e, 'tile_x', None):
        y = e.tile_y * 8 * self.scale
        x = e.tile_x * 8 * self.scale
        self.draw_error(y, x, s)
      elif getattr(e, 'block_y', None) and getattr(e, 'block_x', None):
        y = e.block_y * 16 * self.scale
        x = e.block_x * 16 * self.scale
        self.draw_error(y, x, s * 2)
    self.save_file()

  # create_grid_view
  #
  # Create an image that shows the blocks and tiles.
  #
  # outfile: Filename to output the grid view to.
  # img: Input pixel art image.
  def create_grid_view(self, outfile, img):
    self.scale = SCALE_FACTOR
    width, height = (256 * self.scale, 240 * self.scale)
    self.img = img.resize((width, height), Image.NEAREST).convert('RGB')
    self.draw = ImageDraw.Draw(self.img)
    self.outfile = outfile
    self.draw_grid(width, height)
    self.save_file()

