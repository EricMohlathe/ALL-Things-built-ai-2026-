//+------------------------------------------------------------------+
//| OF_ChartTheme.mqh — centralised colors, fonts, layout constants  |
//| Include once. Edit constants to retheme entire EA.               |
//+------------------------------------------------------------------+
#property strict

// ---------- PALETTE ----------
#define OF_BG              C'11,16,24'      // panel bg
#define OF_BG2             C'18,24,36'      // alt bg
#define OF_LINE            C'40,52,68'      // grid lines / borders
#define OF_TEXT            C'200,210,220'
#define OF_DIM             C'120,128,140'
#define OF_OK              C'43,200,140'    // bull/pass
#define OF_FAIL            C'230,80,100'    // bear/fail
#define OF_WAIT            C'240,170,80'    // amber waiting
#define OF_ACCENT          C'110,170,255'   // links / VP highlights
#define OF_POC             C'200,80,220'    // magenta POC
#define OF_VAH_VAL         C'80,170,255'    // dodgerblue
#define OF_LVN             C'255,220,80'    // yellow LVN
#define OF_HVN             C'80,200,120'    // green HVN
#define OF_ICEBERG         C'180,80,255'    // purple iceberg
#define OF_STAR            C'255,200,60'    // gold star
#define OF_SESSION_LDN     C'40,80,160'     // semi-transparent applied at draw
#define OF_SESSION_NY      C'200,120,40'

// ---------- FONTS ----------
#define OF_FONT            "Consolas"       // monospace for numeric alignment
#define OF_FONT_BOLD       "Consolas Bold"
#define OF_FONT_TITLE      "Segoe UI Semibold"
#define OF_FONT_SIZE       10
#define OF_FONT_SIZE_LG    12
#define OF_FONT_SIZE_SM    8

// ---------- LAYOUT ----------
#define OF_DASH_W          380
#define OF_DASH_PAD        10
#define OF_DASH_ROW_H      20
#define OF_DASH_CORNER     CORNER_RIGHT_UPPER
#define OF_DASH_X          16
#define OF_DASH_Y          22

// ---------- TRANSPARENCY ----------
// MT5 uses ARGB; alpha is the high byte. Helper:
#define OF_ARGB(a,r,g,b)   ((uint)((a<<24)|(r<<16)|(g<<8)|b))
#define OF_ALPHA_HEAVY     220
#define OF_ALPHA_MED       150
#define OF_ALPHA_LIGHT     90
#define OF_ALPHA_GHOST     40

// ---------- OBJECT NAME PREFIX ----------
// Single prefix everywhere → trivial cleanup with ObjectsDeleteAll.
#define OF_PREFIX          "GODMODE_"
//+------------------------------------------------------------------+
