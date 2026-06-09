//+------------------------------------------------------------------+
//| OF_VPHeatmap.mqh                                                 |
//| Bookmap-style horizontal volume-profile heatmap rendered as a    |
//| single canvas bitmap label. Cheap to redraw, scales with chart.  |
//+------------------------------------------------------------------+
#property strict
#include <Canvas/Canvas.mqh>
#include "OF_ChartTheme.mqh"

class COFVPHeatmap
  {
private:
   CCanvas           m_c;
   string            m_name;
   int               m_w;
   int               m_h;

   uint              ToARGB(const color clr, const uchar a) { return ColorToARGB(clr, a); }

public:
   bool              Init(const string name = OF_PREFIX + "VPHeat",
                          const int width = 80, const int height = 480,
                          const int x = 16, const int y = 60,
                          const int corner = CORNER_LEFT_LOWER)
     {
      m_name = name; m_w = width; m_h = height;
      if(!m_c.CreateBitmapLabel(name, x, y, width, height, COLOR_FORMAT_ARGB_NORMALIZE)) return(false);
      ObjectSetInteger(0, name, OBJPROP_CORNER, corner);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      return(true);
     }

   void              Destroy() { m_c.Destroy(); ObjectDelete(0, m_name); }

   // bin_vol: oldest-first volume per price bin (low→high price).
   // poc_idx: bin index of POC for highlight.
   void              Render(const double &bin_vol[], const int poc_idx)
     {
      m_c.Erase(0x00000000);
      int bins = ArraySize(bin_vol);
      // Clamp to a safe upper bound — pixel-fill is O(bins) per render and
      // unbounded bin counts can stall the chart on attach.
      const int MaxBins = 500;
      if(bins > MaxBins) bins = MaxBins;
      if(bins == 0) { m_c.Update(); return; }
      double maxV = 0; for(int i = 0; i < bins; i++) if(bin_vol[i] > maxV) maxV = bin_vol[i];
      if(maxV <= 0) maxV = 1;
      double rowH = (double)m_h / bins;
      for(int i = 0; i < bins; i++)
        {
         double pct = bin_vol[i] / maxV;
         int barW = (int)(pct * (m_w - 4));
         int yTop = (int)((bins - 1 - i) * rowH);
         int yBot = (int)((bins - i) * rowH);
         uchar a = (uchar)(OF_ALPHA_LIGHT + pct * (OF_ALPHA_HEAVY - OF_ALPHA_LIGHT));
         color clr = (i == poc_idx) ? OF_POC : OF_ACCENT;
         m_c.FillRectangle(2, yTop, 2 + barW, yBot, ToARGB(clr, a));
        }
      // outer frame
      m_c.Rectangle(0, 0, m_w - 1, m_h - 1, ToARGB(OF_LINE, OF_ALPHA_MED));
      m_c.Update();
     }
  };
//+------------------------------------------------------------------+
