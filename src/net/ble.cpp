#include "ble.h"
#include <NimBLEDevice.h>

namespace net {

static const char *SVC_UUID = "177b0001-6f32-4ea3-b878-866e7628de1f";
static const char *ING_UUID = "177b0002-6f32-4ea3-b878-866e7628de1f";
static const char *OUT_UUID = "177b0003-6f32-4ea3-b878-866e7628de1f";

static volatile bool g_connected = false;
static NimBLECharacteristic *g_out = nullptr;
static bool g_enabled = true; // the "BT" setting
static bool g_begun = false;  // begin() has run (the hub started us)
static bool g_inited = false; // NimBLE server built (only ever once)

// NimBLE callbacks run on the NimBLE host task: only hand the bytes to the
// hub's queue (it copies them); parsing happens on the loop task.
class IngressCb : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic *c) override {
    NimBLEAttValue v = c->getValue();
    submit((const char *)v.data(), v.length(), SRC_BLE);
  }
};

class SrvCb : public NimBLEServerCallbacks {
  void onConnect(NimBLEServer *) override { g_connected = true; }
  void onDisconnect(NimBLEServer *) override { g_connected = false; }
};

static IngressCb g_ingressCb;
static SrvCb g_srvCb;

// Build the GATT server once, then (re)start advertising.
static void startBle() {
  if (g_inited) {
    NimBLEDevice::getServer()->advertiseOnDisconnect(true);
    NimBLEDevice::getAdvertising()->start();
    Serial.println("[ble] advertising again");
    return;
  }
  g_inited = true;
  NimBLEDevice::init("claude-cyd");
  NimBLEDevice::setMTU(517); // event envelopes (~400B) fit one write
  NimBLEServer *srv = NimBLEDevice::createServer();
  srv->setCallbacks(&g_srvCb);
  srv->advertiseOnDisconnect(true);
  NimBLEService *svc = srv->createService(SVC_UUID);
  NimBLECharacteristic *ing =
      svc->createCharacteristic(ING_UUID, NIMBLE_PROPERTY::WRITE);
  ing->setCallbacks(&g_ingressCb);
  g_out = svc->createCharacteristic(OUT_UUID, NIMBLE_PROPERTY::READ |
                                                  NIMBLE_PROPERTY::NOTIFY);
  g_out->setValue("{\"decision\":\"\"}");
  svc->start();
  NimBLEAdvertising *adv = NimBLEDevice::getAdvertising();
  adv->addServiceUUID(SVC_UUID);
  adv->start();
  Serial.println("[ble] advertising as claude-cyd");
}

// Go dark: no advertising, no auto-readvertise, and drop any connected host.
static void stopBle() {
  if (!g_inited)
    return;
  NimBLEServer *srv = NimBLEDevice::getServer();
  srv->advertiseOnDisconnect(false);
  NimBLEDevice::getAdvertising()->stop();
  for (uint16_t conn : srv->getPeerDevices())
    srv->disconnect(conn);
  g_connected = false;
  Serial.println("[ble] off");
}

void BleTransport::begin() {
  g_begun = true;
  if (g_enabled)
    startBle();
  else
    Serial.println("[ble] off (Settings -> BT)");
}

void BleTransport::setEnabled(bool on) {
  if (on == g_enabled)
    return;
  g_enabled = on;
  if (!g_begun)
    return; // begin() applies it
  if (on)
    startBle();
  else
    stopBle();
}

bool BleTransport::up(uint32_t) const { return g_enabled && g_connected; }

void BleTransport::send(const char *json) {
  if (!g_out || !g_enabled)
    return;
  g_out->setValue(json);
  if (g_connected)
    g_out->notify();
}

} // namespace net
