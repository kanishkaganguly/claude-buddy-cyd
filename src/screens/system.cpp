#include "system.h"
#include "net/hub.h"
#include "render/character.h"
#include "ui/text.h"
#include "ui/theme.h"

namespace screens {

using net::AppState;

static const int ROWS = 3;
static const int GW = 2 * AppState::SYS_N; // one 2-px column per sample
static const int GH = 26;                  // graph height
static const uint32_t STALE_MS = 8000;     // no sample this long -> "paused"
static const char *const LABEL[ROWS] = {"CPU", "GPU", "RAM"};

// Geometry, in ONE place so the full page and the live refresh agree.
static int cardY(int yOrg) { return render::REG_Y + render::REG_H + 4 - yOrg; }
static int rowY(int cy, int r) { return cy + 28 + r * 33; }
static int graphX() { return ui::tft().width() - 16 - GW; }

static const uint8_t *series(const AppState &s, int r) {
  return r == 0 ? s.sysCpu : r == 1 ? s.sysGpu : s.sysRam;
}

static uint16_t rowColor(const ui::CardPal &p, int r) {
  return r == 0 ? p.coral : r == 1 ? p.gpu : p.ram;
}

static bool fresh(const AppState &s) {
  return s.sysCount > 0 && millis() - s.sysAt < STALE_MS;
}

static const char *statusText(const AppState &s) {
  return s.sysCount == 0 ? "waiting" : fresh(s) ? "live" : "paused";
}

// The row's current reading: "23%", "n/a" (no such device), or "--" (no data,
// or the bridge went quiet -- the graph keeps the last history either way).
static void valueText(const AppState &s, int r, char *out, size_t n) {
  if (!fresh(s)) {
    snprintf(out, n, "--");
    return;
  }
  uint8_t v = series(s, r)[(s.sysHead + AppState::SYS_N - 1) % AppState::SYS_N];
  if (v > 100)
    snprintf(out, n, "n/a");
  else
    snprintf(out, n, "%d%%", v);
}

// Plot one series into `c` with the graph's top-left at (ox, oy): a filled
// column per sample, newest at the right edge, over a baseline.
static void plotRow(TFT_eSPI &c, int ox, int oy, const AppState &s, int r,
                    uint16_t col, uint16_t base) {
  const uint8_t *v = series(s, r);
  for (int age = 0; age < s.sysCount; age++) {
    uint8_t pct = v[(s.sysHead - 1 - age + 2 * AppState::SYS_N) % AppState::SYS_N];
    if (pct > 100)
      continue; // n/a sample: leave a gap
    int h = pct * (GH - 1) / 100;
    if (pct > 0 && h < 1)
      h = 1; // any load stays visible
    if (h > 0)
      c.fillRect(ox + GW - 2 * (age + 1), oy + GH - 1 - h, 2, h, col);
  }
  c.drawFastHLine(ox, oy + GH - 1, GW, base);
}

void drawSystemPage(TFT_eSPI &c, int yOrg, const ui::CardPal &p) {
  const AppState &s = net::hub.state();
  int W = ui::tft().width(), H = ui::tft().height();
  int cy = cardY(yOrg);
  int chh = H - (render::REG_Y + render::REG_H + 4) - 6;
  c.fillRoundRect(8, cy, W - 16, chh, 12, p.card);
  ui::gtextC(c, "System", 18, cy + 14, &FreeSansBold9pt7b, p.text, p.card,
             ML_DATUM);
  ui::gtextC(c, statusText(s), W - 18, cy + 14, &FreeSans9pt7b, p.muted,
             p.card, MR_DATUM);
  char val[8];
  for (int r = 0; r < ROWS; r++) {
    int y = rowY(cy, r);
    ui::gtextC(c, LABEL[r], 18, y + 8, &FreeSansBold9pt7b, p.text, p.card,
               ML_DATUM);
    valueText(s, r, val, sizeof(val));
    ui::gtextC(c, val, 18, y + 24, &FreeSans9pt7b, rowColor(p, r), p.card,
               ML_DATUM);
    plotRow(c, graphX(), y + 3, s, r, rowColor(p, r), p.divider);
  }
}

void renderSystem(bool full) {
  TFT_eSPI &t = ui::tft();
  const AppState &s = net::hub.state();
  int W = t.width();
  int cy = cardY(0);

  // live refresh: throttle + only when a sample arrived or the status changed
  static uint32_t lastSeq = 0xFFFFFFFF, lastDraw = 0;
  static const char *lastStatus = nullptr;
  const char *status = statusText(s);
  if (!full) {
    uint32_t nowMs = millis();
    if (nowMs - lastDraw < 500)
      return;
    if (s.sysSeq == lastSeq && status == lastStatus)
      return;
    lastDraw = nowMs;
  }
  lastSeq = s.sysSeq;
  lastStatus = status;

  if (full) {
    drawSystemPage(t, 0, ui::PAL_RGB);
    return;
  }

  ui::blitText(W - 96, cy + 4, 80, 20, status, W - 18, cy + 14, &FreeSans9pt7b,
               C_MUTED, C_CARD, MR_DATUM, 78);
  char val[8];
  for (int r = 0; r < ROWS; r++) {
    int y = rowY(cy, r);
    uint16_t col = rowColor(ui::PAL_RGB, r);
    valueText(s, r, val, sizeof(val));
    ui::blitText(16, y + 16, graphX() - 20, 18, val, 18, y + 24,
                 &FreeSans9pt7b, col, C_CARD, ML_DATUM, graphX() - 22);
    // each graph swaps in from an off-screen sprite (a direct redraw flickers)
    TFT_eSprite spr(&t);
    spr.setColorDepth(16);
    if (spr.createSprite(GW, GH)) {
      spr.fillSprite(C_CARD);
      plotRow(spr, 0, 0, s, r, col, ui::PAL_RGB.divider);
      spr.pushSprite(graphX(), y + 3);
      spr.deleteSprite();
    } else { // low heap -> direct draw (may flicker)
      t.fillRect(graphX(), y + 3, GW, GH, C_CARD);
      plotRow(t, graphX(), y + 3, s, r, col, ui::PAL_RGB.divider);
    }
  }
}

} // namespace screens
