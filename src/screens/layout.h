#pragma once
#include <TFT_eSPI.h>
#include "ui/widgets.h"

namespace screens {

// Shared tap-target layout, computed once from the panel size at boot: the
// bottom Deny/Approve action bar (ask screen), the Settings rows, and the
// "Got it" pill on the needs-you screen.
extern ui::Rect denyBtn, approveBtn;
extern ui::Rect ackBtn; // "Got it" pill on the needs-you screen (dismisses -> idle)
// Settings buttons, top to bottom; Quiet and BT share a row as two halves.
enum SetBtn {
  SB_POWER, SB_STATS, SB_QUIET, SB_BT, SB_BRIGHT, SB_SCREEN, SB_RECAL,
  SB_CLOSE, SET_BTN_N
};
extern ui::Rect setBtns[SET_BTN_N];

void computeButtons(TFT_eSPI &t);

} // namespace screens
