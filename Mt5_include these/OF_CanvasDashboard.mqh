//+------------------------------------------------------------------+
//| OF_CanvasDashboard.mqh                                           |
//| Canvas-based dashboard: gradients, rounded corners, antialiased  |
//| text. Uses MT5 Standard Library <Canvas/Canvas.mqh>.             |
//+------------------------------------------------------------------+
#property strict
#include <Canvas/Canvas.mqh>
#include "OF_ChartTheme.mqh"

class COFDashboard
  {
private:
   CCanvas           m_c;
   int               m_w;
   int               m_h;
   string            m_name;
   int               m_corner;
   bool              m_ready;  // tracks successful CreateBitmapLabel

   uint              C(const color clr, const uchar a = OF_ALPHA_HEAVY)
     { return ColorToARGB(clr, a); }

   void              RoundRect(const int x, const int y, const int w, const int h,
                               const int r, const uint clr)
     {
      // simple rounded rect via filled rect + corner circles
      m_c.FillRectangle(x + r, y,         x + w - r, y + h,         clr);
      m_c.FillRectangle(x,     y + r,     x + w,     y + h - r,     clr);
      m_c.FillCircle(x + r,         y + r,         r, clr);
      m_c.FillCircle(x + w - r - 1, y + r,         r, clr);
      m_c.FillCircle(x + r,         y + h - r - 1, r, clr);
      m_c.FillCircle(x + w - r - 1, y + h - r - 1, r, clr);
     }

   void              GradientBar(const int x, const int y, const int w, const int h,
                                 const uint top, const uint bot)
     {
      for(int i = 0; i < h; i++)
        {
         double t = (double)i / (double)h;
         uchar ar = (uchar)((top >> 16) & 0xFF), ag = (uchar)((top >> 8) & 0xFF), ab = (uchar)(top & 0xFF), aa = (uchar)((top >> 24) & 0xFF);
         uchar br = (uchar)((bot >> 16) & 0xFF), bg = (uchar)((bot >> 8) & 0xFF), bb = (uchar)(bot & 0xFF), ba = (uchar)((bot >> 24) & 0xFF);
         uchar r = (uchar)(ar + t * (br - ar));
         uchar g = (uchar)(ag + t * (bg - ag));
         uchar b = (uchar)(ab + t * (bb - ab));
         uchar a = (uchar)(aa + t * (ba - aa));
         uint  cc = (uint)((a << 24) | (r << 16) | (g << 8) | b);
         m_c.LineHorizontal(x, x + w - 1, y + i, cc);
        }
     }

public:
   bool              Init(const string name = OF_PREFIX + "Dashboard",
                          const int width = OF_DASH_W, const int height = 280,
                          const int corner = OF_DASH_CORNER,
                          const int x = OF_DASH_X, const int y = OF_DASH_Y)
     {
      m_name = name; m_w = width; m_h = height; m_corner = corner; m_ready = false;
      if(!m_c.CreateBitmapLabel(name, x, y, width, height, COLOR_FORMAT_ARGB_NORMALIZE))
         return(false);
      ObjectSetInteger(0, name, OBJPROP_CORNER, corner);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      m_ready = true;
      Clear();
      m_c.Update();
      return(true);
     }

   bool              IsReady() const { return m_ready; }

   void              Destroy() { m_c.Destroy(); ObjectDelete(0, m_name); m_ready = false; }

   void              Clear()
     {
      if(!m_ready) return;
      m_c.Erase(0x00000000);
      // panel
      RoundRect(0, 0, m_w, m_h, 8, C(OF_BG, OF_ALPHA_HEAVY));
      // top accent gradient bar
      GradientBar(0, 0, m_w, 4, C(OF_ACCENT, OF_ALPHA_HEAVY), C(OF_ACCENT, 0));
      // 1px border
      m_c.Rectangle(0, 0, m_w - 1, m_h - 1, C(OF_LINE, OF_ALPHA_MED));
     }

   void              Title(const string text, const int y = 10)
     {
      if(!m_ready) return;
      m_c.FontSet(OF_FONT_TITLE, -13 * 10, FW_SEMIBOLD);
      m_c.TextOut(OF_DASH_PAD, y, text, C(OF_TEXT));
     }

   void              Row(const int idx, const string label, const string value, const color dot = OF_DIM)
     {
      if(!m_ready) return;
      int y = 36 + idx * OF_DASH_ROW_H;
      m_c.FillCircle(OF_DASH_PAD + 4, y + 7, 4, C(dot));
      m_c.FontSet(OF_FONT, -OF_FONT_SIZE * 10, FW_NORMAL);
      m_c.TextOut(OF_DASH_PAD + 16, y, label, C(OF_DIM));
      m_c.TextOut(m_w - OF_DASH_PAD - 4 - m_c.TextWidth(value), y, value, C(OF_TEXT));
     }

   void              Sep(const int y) { if(m_ready) m_c.LineHorizontal(8, m_w - 8, y, C(OF_LINE, OF_ALPHA_LIGHT)); }
   void              Update() { if(m_ready) m_c.Update(); }
   CCanvas*          Canvas() { return GetPointer(m_c); }
  };
//+------------------------------------------------------------------+
