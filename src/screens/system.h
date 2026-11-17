#pragma once
#include <TFT_eSPI.h>
#include "ui/theme.h"

namespace screens {

// System card: the third page of the home screen's bottom card (swipe left from
// trends). CPU / GPU / RAM utilisation of the PC running the bridge, sent every
// ~2 s while Claude is active; each row graphs the last ~2 minutes, newest at
// the right. full=true paints the whole card; full=false is the throttled live
// refresh (graphs, values and status only, flicker-free).
void renderSystem(bool full);

// Draw the full System page onto any canvas (yOrg translates screen-y into
// canvas space; 0 = the screen). Used by the full repaint and by the
// card-slide snapshots (ui::PAL_IDX + 4bpp palette sprite).
void drawSystemPage(TFT_eSPI &c, int yOrg, const ui::CardPal &p);

} // namespace screens
