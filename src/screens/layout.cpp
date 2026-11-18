#include "layout.h"
#include "render/character.h"

namespace screens {

ui::Rect denyBtn, approveBtn;
ui::Rect ackBtn;
ui::Rect setBtns[SET_BTN_N];

void computeButtons(TFT_eSPI &t) {
  int W = t.width(), H = t.height();
  int bh = 56, m = 8;
  denyBtn = {m, H - bh - 6, (W - 3 * m) / 2, bh};
  approveBtn = {denyBtn.x + denyBtn.w + m, H - bh - 6, (W - 3 * m) / 2, bh};
  // Settings: 7 rows fit 240x320 (the last ends at 266); Quiet and BT split
  // one row so the buttons stay a comfortable 28 px tall
  int y = 46, sbh = 28, gap = 4, sx = 20, sw = W - 40, half = (sw - gap) / 2;
  for (int i = 0; i < SET_BTN_N; i++) {
    if (i == SB_QUIET) {
      setBtns[i] = {sx, y, half, sbh};
      continue; // BT takes the rest of this row
    }
    if (i == SB_BT)
      setBtns[i] = {sx + half + gap, y, sw - half - gap, sbh};
    else
      setBtns[i] = {sx, y, sw, sbh};
    y += sbh + gap;
  }
  // "Got it" button: the cardless needs-you screen frees the whole lower third,
  // so centre a roomy pill there as the dismiss call-to-action.
  int aw = 150, ah = 46, cardTop = render::REG_Y + render::REG_H;
  ackBtn = {(W - aw) / 2, cardTop + (H - cardTop - ah) / 2, aw, ah};
}

} // namespace screens
