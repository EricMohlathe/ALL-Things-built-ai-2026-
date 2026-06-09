//+------------------------------------------------------------------+
//| OF_Toast.mqh                                                     |
//| Stacked corner toast notifications with auto-fade.               |
//| Canvas-based, antialiased. Call Show(); call Tick() each tick.   |
//+------------------------------------------------------------------+
#property strict
#include <Canvas/Canvas.mqh>
#include "OF_ChartTheme.mqh"

#define OF_TOAST_W      280
#define OF_TOAST_H       46
#define OF_TOAST_GAP      6
#define OF_TOAST_MAX      4
#define OF_TOAST_LIFE_MS 5000   // total visible time
#define OF_TOAST_FADE_MS 1200   // fade-out window

class COFToast
  {
private:
   struct Entry { string name; ulong born_ms; CCanvas *c; color accent; string title; string body; };
   Entry             m_items[];
   int               m_x;
   int               m_y;
   int               m_corner;

   uint              ToARGB(const color clr, const uchar a) { return ColorToARGB(clr, a); }

   void              Draw(Entry &e, const uchar alpha)
     {
      e.c.Erase(0x00000000);
      // background
      e.c.FillRectangle(0, 0, OF_TOAST_W, OF_TOAST_H, ToARGB(OF_BG, alpha));
      e.c.FillRectangle(0, 0, 4,           OF_TOAST_H, ToARGB(e.accent, alpha));
      e.c.Rectangle(0, 0, OF_TOAST_W - 1, OF_TOAST_H - 1, ToARGB(OF_LINE, (uchar)(alpha * 0.7)));
      e.c.FontSet(OF_FONT_BOLD, -OF_FONT_SIZE * 10, FW_BOLD);
      e.c.TextOut(14, 6, e.title, ToARGB(OF_TEXT, alpha));
      e.c.FontSet(OF_FONT, -OF_FONT_SIZE_SM * 10, FW_NORMAL);
      e.c.TextOut(14, 24, e.body, ToARGB(OF_DIM, alpha));
      e.c.Update();
     }

public:
   void              Init(const int corner = CORNER_RIGHT_LOWER,
                          const int x = 16, const int y = 16)
     { m_corner = corner; m_x = x; m_y = y; }

   void              Show(const string title, const string body, const color accent = OF_ACCENT)
     {
      // evict oldest if over cap
      while(ArraySize(m_items) >= OF_TOAST_MAX)
        {
         m_items[0].c.Destroy();
         ObjectDelete(0, m_items[0].name);
         for(int i = 0; i < ArraySize(m_items) - 1; i++) m_items[i] = m_items[i + 1];
         ArrayResize(m_items, ArraySize(m_items) - 1);
        }
      Entry e;
      e.name   = StringFormat(OF_PREFIX + "Toast_%llu", GetMicrosecondCount());
      e.born_ms = (ulong)GetTickCount();
      e.accent = accent; e.title = title; e.body = body;
      e.c = new CCanvas();
      int idx = ArraySize(m_items);
      int yOff = m_y + idx * (OF_TOAST_H + OF_TOAST_GAP);
      if(!e.c.CreateBitmapLabel(e.name, m_x, yOff, OF_TOAST_W, OF_TOAST_H, COLOR_FORMAT_ARGB_NORMALIZE)) return;
      ObjectSetInteger(0, e.name, OBJPROP_CORNER, m_corner);
      ObjectSetInteger(0, e.name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, e.name, OBJPROP_HIDDEN, true);
      ArrayResize(m_items, idx + 1);
      m_items[idx] = e;
      Draw(m_items[idx], OF_ALPHA_HEAVY);
     }

   void              Tick()
     {
      ulong now = (ulong)GetTickCount();
      for(int i = ArraySize(m_items) - 1; i >= 0; i--)
        {
         ulong age = now - m_items[i].born_ms;
         if(age >= OF_TOAST_LIFE_MS)
           {
            m_items[i].c.Destroy(); ObjectDelete(0, m_items[i].name); delete m_items[i].c;
            for(int j = i; j < ArraySize(m_items) - 1; j++) m_items[j] = m_items[j + 1];
            ArrayResize(m_items, ArraySize(m_items) - 1);
            continue;
           }
         uchar a = OF_ALPHA_HEAVY;
         if(age > OF_TOAST_LIFE_MS - OF_TOAST_FADE_MS)
           {
            double k = 1.0 - (double)(age - (OF_TOAST_LIFE_MS - OF_TOAST_FADE_MS)) / OF_TOAST_FADE_MS;
            a = (uchar)MathMax(0.0, k * OF_ALPHA_HEAVY);
           }
         Draw(m_items[i], a);
        }
     }

   void              Destroy()
     {
      for(int i = 0; i < ArraySize(m_items); i++)
        { m_items[i].c.Destroy(); ObjectDelete(0, m_items[i].name); delete m_items[i].c; }
      ArrayResize(m_items, 0);
     }
  };
//+------------------------------------------------------------------+
