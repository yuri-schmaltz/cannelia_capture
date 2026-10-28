# SPDX-License-Identifier: GPL-2.0-or-later
# Cannelia Capture modifications (C) 2026 yuri-schmaltz; modified 2026-10-28.
# Derived components: Linux Mint / Cinnamon contributors. See NOTICE.md.
"""Crop geometry in image pixels, independent of zoom and widget allocation."""
class Selection:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.rect = None
        self.drag = None

    def handles(self):
        if self.rect is None:
            return {}
        x, y, w, h = self.rect
        return {'nw': (x, y), 'n': (x+w/2, y), 'ne': (x+w, y),
                'e': (x+w, y+h/2), 'se': (x+w, y+h), 's': (x+w/2, y+h),
                'sw': (x, y+h), 'w': (x, y+h/2)}

    def begin(self, x, y, scale=1):
        if not 0 <= x <= self.width or not 0 <= y <= self.height:
            return False
        mode = 'new'
        if self.rect:
            tolerance = 7 / max(scale, 0.01)
            nearby = [(abs(hx-x)+abs(hy-y), name) for name, (hx, hy) in self.handles().items()
                      if abs(hx-x) <= tolerance and abs(hy-y) <= tolerance]
            if nearby:
                mode = min(nearby)[1]
            else:
                rx, ry, rw, rh = self.rect
                if rx <= x <= rx+rw and ry <= y <= ry+rh:
                    mode = 'move'
        self.drag = (mode, x, y, self.rect)
        if mode == 'new':
            self.rect = None
        return True

    def update(self, x, y):
        if self.drag is None:
            return
        x, y = max(0, min(x, self.width)), max(0, min(y, self.height))
        mode, sx, sy, original = self.drag
        if mode == 'new':
            left, right = sorted((sx, x))
            top, bottom = sorted((sy, y))
        elif mode == 'move':
            ox, oy, w, h = original
            left = max(0, min(ox+x-sx, self.width-w))
            top = max(0, min(oy+y-sy, self.height-h))
            right, bottom = left+w, top+h
        else:
            left, top, w, h = original
            right, bottom = left+w, top+h
            if 'w' in mode:
                left = min(x, right-1)
            if 'e' in mode:
                right = max(x, left+1)
            if 'n' in mode:
                top = min(y, bottom-1)
            if 's' in mode:
                bottom = max(y, top+1)
        left, top, right, bottom = (int(v) for v in (left, top, right, bottom))
        self.rect = (left, top, right-left, bottom-top) if right > left and bottom > top else None

    def end(self, x, y):
        self.update(x, y)
        self.drag = None
