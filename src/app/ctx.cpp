#include "ctx.h"

namespace app {

Ctx ctx;

const uint32_t kScreenOffMs[SCREEN_OFF_N] = {30000UL, 120000UL, 300000UL,
                                             900000UL, 0};
const char *const kScreenOffLabel[SCREEN_OFF_N] = {"30 s", "2 min", "5 min",
                                                   "15 min", "never"};

} // namespace app
