/*
    PID test platform on Arduino Yun

    Air flow Control platform :
    - Output is PWM connect to MOSFET to drive fan
    - ECV output is 0.4/2V map to 0/25 m3/h

    Cyclic output with process value, output (0/100%), set point for arduino serial plotter

    Send commands via serial monitor :
    - "MAN" for set PID to manual mode, "AUTO" for automatic mode, "SP 34.2" for fix setpoint at 34.2
    - "KP 2.55" to set kp at 2.55, "KI 2" ti set ki at 2.0, "KD 0.2" to set kd at 0.2
    - "SAVE" write currents params (SP, kp, ki and kd) to EEPROM

    This code is licensed under the MIT license : http://opensource.org/licenses/MIT
*/

#include <EEPROM.h>
// from https://github.com/br3ttb/Arduino-PID-Library
#include <PID_v1.h>
// from https://github.com/fdebrabander/Arduino-LiquidCrystal-I2C-library
#include <LiquidCrystal_I2C.h>
// from https://github.com/bblanchon/ArduinoJson
#include <ArduinoJson.h>
// from https://github.com/arkhipenko/TaskScheduler
#include <TaskScheduler.h>

// some const
// I/O
#define FLOW_INPUT          A0
#define OUT_PWM             11
// serial commands
#define CMD_TIMEOUT         10E3
#define MAX_CMD_SIZE        64
// LCD display
#define LCD_LINE_SIZE       20
#define MAX_CMD_SIZE        64
// EEPROM storage
#define EEPROM_MAGIC_NB     0xAA55
#define EEPROM_AD_MAGIG_NB  0
#define EEPROM_AD_PID_P     sizeof(uint16_t)
#define EEPROM_AD_PID_SP    sizeof(uint16_t) + sizeof(PidParams)

// some struct
// define struct with defaults values
struct PidParams {
  double kp = 6.0;
  double ki = 0.75;
  double kd = 0.25;
};

// some vars
// LCD: address to 0x27 for a 20 chars and 4 line display
LiquidCrystal_I2C lcd(0x27, 20, 4);
// PID
PidParams pid_p;
double pid_sp = 32.0;
double pid_pv = 0.0;
double pid_out = 0.0;
PID myPID(&pid_pv, &pid_out, &pid_sp, 0, 0, 0, DIRECT);
// task scheduler
Scheduler runner;

// some prototypes
void task_serial_command();
void task_lcd();
void task_pid();

// some tasks
Task t_cmd(1, TASK_FOREVER, &task_serial_command, &runner, true);
Task t_lcd(200 * TASK_MILLISECOND, TASK_FOREVER, &task_lcd, &runner, true);
Task t_pid(1 * TASK_SECOND, TASK_FOREVER, &task_pid, &runner, true);

// print msg on line nb on LCD panel
// pad the line with space char
void lcd_line(byte line, String msg) {
  // limit size of message
  msg.remove(LCD_LINE_SIZE);
  // set pos at begin of a line
  lcd.setCursor(0, line);
  lcd.print(msg);
  // pad with char
  for (byte i = 0; i < LCD_LINE_SIZE - msg.length(); i++)
    lcd.write(' ');
}

void task_serial_command() {
  // local static vars
  static String cmd_rx_buf = "";
  static bool cmd_echo_mode = false;
  static uint32_t cmd_t_last_char = 0;
  // check command
  while (Serial1.available() > 0) {
    // receive loop
    while (true) {
      int inByte = Serial1.read();
      // no more data
      if (inByte == -1)
        break;
      // manage backspace
      if ((inByte == 0x08) or (inByte == 0x7f)) {
        // remove last char in buffer
        cmd_rx_buf.remove(cmd_rx_buf.length() - 1);
        // send backspace + ' ' + backspace
        Serial1.print((char) 8);
        Serial1.print(' ');
        Serial1.print((char) 8);
        break;
      }
      // if echo on
      if (cmd_echo_mode)
        Serial1.print((char) inByte);
      // reset command buffer if the last rx is too old
      if (millis() - cmd_t_last_char > CMD_TIMEOUT)
        cmd_rx_buf = "";
      cmd_t_last_char = millis();
      // add data to s_cmd
      cmd_rx_buf += (char) inByte;
      // limit size to MAX_CMD_SIZE
      if (cmd_rx_buf.length() > MAX_CMD_SIZE)
        cmd_rx_buf.remove(0, cmd_rx_buf.length() - MAX_CMD_SIZE);
      // pause receive loop if \n occur
      if (inByte == '\n')
        break;
    }
    // skip command not ended with "\n"
    if (! cmd_rx_buf.endsWith("\n"))
      break;
    // remove leading and trailing \r\n, force case
    cmd_rx_buf.trim();
    cmd_rx_buf.toLowerCase();
    // check for command argument (cmd [space char] [arg])
    int index_space  = cmd_rx_buf.indexOf(" ");
    String s_arg = "";
    String s_cmd = cmd_rx_buf;
    if (index_space != -1) {
      s_cmd = cmd_rx_buf.substring(0, index_space);
      s_arg = cmd_rx_buf.substring(index_space + 1);
      s_arg.trim();
      s_arg.toLowerCase();
    }
    // check command
    if (s_cmd.equals("json")) {
      // build message
      StaticJsonBuffer<200> jsonBuffer;
      JsonObject& root = jsonBuffer.createObject();
      root["pv"] = pid_pv;
      root["out"] = pid_out;
      root["sp"] = pid_sp;
      // send it
      root.printTo(Serial1);
      Serial1.println();
    }
    else if (s_cmd.equals("pid")) {
      String pid_mode = (myPID.GetMode() == AUTOMATIC) ? "AUT" : "MAN";
      Serial1.println("SP  " + String(pid_sp) + " m3/h");
      Serial1.println("PV  " + String(pid_pv) + " m3/h");
      Serial1.println("OUT " + String(pid_out) + " %");
      Serial1.println("PID " + String(pid_p.kp, 1) + "/" + String(pid_p.ki, 1) + "/" + String(pid_p.kd, 1) + " " + pid_mode);
    }
    else if (s_cmd.equals("auto")) {
      Serial1.println(F("PID set to auto mode"));
      myPID.SetMode(AUTOMATIC);
    }
    else if (s_cmd.equals("man")) {
      Serial1.println(F("PID set to manual mode"));
      myPID.SetMode(MANUAL);
    }
    else if (s_cmd.equals("out")) {
      if (! s_arg.equals(""))
        pid_out = s_arg.toFloat();
      Serial1.print(F("PID out = "));
      Serial1.println(pid_out);
    }
    else if (s_cmd.equals("sp")) {
      if (! s_arg.equals(""))
        pid_sp = s_arg.toFloat();
      Serial1.print(F("PID SetPoint = "));
      Serial1.println(pid_sp);
    }
    else if (s_cmd.equals("kp")) {
      if (! s_arg.equals(""))
        pid_p.kp = s_arg.toFloat();
      Serial1.print(F("PID kp = "));
      Serial1.println(pid_p.kp);
    }
    else if (s_cmd.equals("ki")) {
      if (! s_arg.equals(""))
        pid_p.ki = s_arg.toFloat();
      Serial1.print(F("PID ki = "));
      Serial1.println(pid_p.ki);
    }
    else if (s_cmd.equals("kd")) {
      if (! s_arg.equals(""))
        pid_p.kd = s_arg.toFloat();
      Serial1.print(F("PID kd = "));
      Serial1.println(pid_p.kd);
    }
    else if (s_cmd.equals("save")) {
      // store magic number, PID params and setpoint
      EEPROM.put(EEPROM_AD_MAGIG_NB, (uint16_t) EEPROM_MAGIC_NB);
      EEPROM.put(EEPROM_AD_PID_P, pid_p);
      EEPROM.put(EEPROM_AD_PID_SP, pid_sp);
      Serial1.println(F("Write params (SP, kp, ki and kd) to EEPROM"));
    }
    else {
      Serial1.println(F("unknown command send \"?\" to view online help"));
    }
    // reset for next one
    cmd_rx_buf = "";
  }
}

void task_lcd() {
  // refresh LCD display
  String pid_mode = (myPID.GetMode() == AUTOMATIC) ? "AUT" : "MAN";
  lcd_line(0, String("SP  " + String(pid_sp) + " m3/h"));
  lcd_line(1, String("PV  " + String(pid_pv) + " m3/h"));
  lcd_line(2, String("OUT " + String(pid_out) + " %"));
  lcd_line(3, String("PID " + String(pid_p.kp, 1) + "/" + String(pid_p.ki, 1) + "/" + String(pid_p.kd, 1) + " " + pid_mode));
}

void task_pid() {
  // read air flow (process value)
  float ecv_v = 5.0 * analogRead(FLOW_INPUT) / 1024;
  pid_pv = ((ecv_v - 0.4) * 25) / 1.6;
  // update PID
  myPID.SetTunings(pid_p.kp, pid_p.ki, pid_p.kd);
  myPID.Compute();
  // set PWM output
  analogWrite(OUT_PWM, map(pid_out, 0.0, 100.0, 0, 255));
}


void setup() {
  // init serial
  Serial.begin(9600);
  Serial1.begin(9600);
  // init IO
  pinMode(FLOW_INPUT, INPUT);
  // init LCD
  lcd.init();
  lcd.backlight();
  // read EEPROM backup value only if EEPROM have a first init (= magic number is set)
  uint16_t eeprom_magic;
  EEPROM.get(EEPROM_AD_MAGIG_NB, eeprom_magic);
  if (eeprom_magic == EEPROM_MAGIC_NB) {
    EEPROM.get(EEPROM_AD_PID_P, pid_p);
    EEPROM.get(EEPROM_AD_PID_SP, pid_sp);
  }
  // init PID
  myPID.SetOutputLimits(0.0, 100.0);
  myPID.SetMode(AUTOMATIC);
}

void loop() {
  // scheduler handler
  runner.execute();
}
