#include <WiFi.h>

const char *ssid = "MSK2";
const char *password = "msk54321";
//const char *ssid = "Wifi_Domotica_IoT";
//const char *password = "domotica.iot";
WiFiServer server(80);
// DHT Temperature & Humidity Sensor
// Unified Sensor Library Example
// Written by Tony DiCola for Adafruit Industries
// Released under an MIT license.

// REQUIRES the following Arduino libraries:
// - DHT Sensor Library: https://github.com/adafruit/DHT-sensor-library
// - Adafruit Unified Sensor Lib: https://github.com/adafruit/Adafruit_Sensor

#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <DHT_U.h>

#define DHTPIN 4     // Digital pin connected to the DHT sensor 
// Feather HUZZAH ESP8266 note: use pins 3, 4, 5, 12, 13 or 14 --
// Pin 15 can work but DHT must be disconnected during program upload.

// Uncomment the type of sensor in use:
//#define DHTTYPE    DHT11     // DHT 11
#define DHTTYPE    DHT22     // DHT 22 (AM2302)
//#define DHTTYPE    DHT21     // DHT 21 (AM2301)

// See guide for details on sensor wiring and usage:
//   https://learn.adafruit.com/dht/overview

DHT_Unified dht(DHTPIN, DHTTYPE);

uint32_t delayMS;

void setup() {
  Serial.begin(9600);
  // Initialize device.
  dht.begin();
  Serial.println(F("DHTxx Unified Sensor Example"));
  // Print temperature sensor details.
  sensor_t sensor;
  dht.temperature().getSensor(&sensor);
  Serial.println(F("------------------------------------"));
  Serial.println(F("Temperature Sensor"));
  Serial.print  (F("Sensor Type: ")); Serial.println(sensor.name);
  Serial.print  (F("Driver Ver:  ")); Serial.println(sensor.version);
  Serial.print  (F("Unique ID:   ")); Serial.println(sensor.sensor_id);
  Serial.print  (F("Max Value:   ")); Serial.print(sensor.max_value); Serial.println(F("°C"));
  Serial.print  (F("Min Value:   ")); Serial.print(sensor.min_value); Serial.println(F("°C"));
  Serial.print  (F("Resolution:  ")); Serial.print(sensor.resolution); Serial.println(F("°C"));
  Serial.println(F("------------------------------------"));
  // Print humidity sensor details.
  dht.humidity().getSensor(&sensor);
  Serial.println(F("Humidity Sensor"));
  Serial.print  (F("Sensor Type: ")); Serial.println(sensor.name);
  Serial.print  (F("Driver Ver:  ")); Serial.println(sensor.version);
  Serial.print  (F("Unique ID:   ")); Serial.println(sensor.sensor_id);
  Serial.print  (F("Max Value:   ")); Serial.print(sensor.max_value); Serial.println(F("%"));
  Serial.print  (F("Min Value:   ")); Serial.print(sensor.min_value); Serial.println(F("%"));
  Serial.print  (F("Resolution:  ")); Serial.print(sensor.resolution); Serial.println(F("%"));
  Serial.println(F("------------------------------------"));
  // Set delay between sensor readings based on sensor details.
  delayMS = sensor.min_delay / 1000;

//============================================ SERVER ============================
  analogReadResolution(10);
  pinMode(15, OUTPUT);            // motor
  pinMode(LED_BUILTIN, OUTPUT);   // alarme
  pinMode(34, INPUT);             // botao
  pinMode(35, INPUT);             // motor sensor 
  pinMode(25, INPUT);             // LUZ LIGDA sensor
  delay(10);
  Serial.println();
  Serial.print("Conectando a ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado. Endereco IP:");
  Serial.println(WiFi.localIP());
  server.begin();

}

void loop() {
  // Delay between measurements.
  delay(delayMS);
  // Get temperature event and print its value.
  sensors_event_t event;
  /*
  dht.temperature().getEvent(&event);
  if (isnan(event.temperature)) {
    Serial.println(F("Error reading temperature!"));
  }
  else {
    Serial.print(F("Temperature: "));
    Serial.print(event.temperature);
    Serial.println(F("°C"));
  }
  // Get humidity event and print its value.
  dht.humidity().getEvent(&event);
  if (isnan(event.relative_humidity)) {
    Serial.println(F("Error reading humidity!"));
  }
  else {
    Serial.print(F("Humidity: "));
    Serial.print(event.relative_humidity);
    Serial.println(F("%"));
  }
  */

//=========================================================SERVER ========================

  WiFiClient client = server.available();
  
  if (client) {
    Serial.println("Novo cliente conectado.");
    String currentLine = "";

    while (client.connected()) {
      if (client.available()) {
        char c = client.read();
        Serial.write(c);

        if (c == '\n' && currentLine.length() == 0) {
          // Enviar cabecalho HTTP
          client.println("HTTP/1.1 200 OK");
          client.println("Content-Type: application/json");
          client.println("Connection: close");
          client.println();

          int botao = digitalRead(34);
          int motorEstado = digitalRead(35);
          int alarmeEstado = digitalRead(25);
          sensors_event_t event;
          dht.temperature().getEvent(&event);
          // Enviar JSON corretamente formatado          
          client.print("[{\"Temperatura\":"); 
          float TEMP = event.temperature;
          client.print(TEMP, 4); 
          client.print(",");
          client.print("\"Umidade\":"); 
          dht.humidity().getEvent(&event);
          float HUM = event.relative_humidity;
          client.print(HUM, 4); 
          client.print(",");
          client.print("\"Botao\":"); 
          client.print(botao); 
          client.print(",");
          client.print("\"Motor\":"); 
          client.print(motorEstado); 
          client.print(",");
          client.print("\"Alarme\":"); 
          client.print(alarmeEstado); 
          client.print("}");
          client.println("]");
          break;
        }

        if (c == '\n') {
          currentLine = "";
        } else if (c != '\r') {
          currentLine += c;
        }

        // Comandos GET para controle
        if (currentLine.endsWith("GET /motor1_h")) {
          digitalWrite(15, HIGH);
        }
        if (currentLine.endsWith("GET /motor1_l")) {
          digitalWrite(15, LOW);
        }
        if (currentLine.endsWith("GET /alarme_h")) {
          digitalWrite(LED_BUILTIN, HIGH);
        }
        if (currentLine.endsWith("GET /alarme_l")) {
          digitalWrite(LED_BUILTIN, LOW);
        }
      }
    }

    client.stop();
    Serial.println("Cliente desconectado.");
  }




}
