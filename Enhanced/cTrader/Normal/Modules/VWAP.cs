using System;
using cAlgo.API;

namespace GodmodeOfea.Enhanced
{
    public class VWAP
    {
        public DateTime Anchor;
        public double CumPV, CumV, CumPV2;
        public double Value;
        public double Sd;

        public void Reset(DateTime t) { Anchor = t; CumPV = 0; CumV = 0; CumPV2 = 0; Value = 0; Sd = 0; }
        public bool IsNewSession(DateTime t) => t.Date != Anchor.Date;
        public void Update(double typPrice, double vol, DateTime t)
        {
            if (Anchor == default || IsNewSession(t)) Reset(t);
            if (vol <= 0) return;
            CumPV += typPrice * vol;
            CumPV2 += typPrice * typPrice * vol;
            CumV  += vol;
            if (CumV > 0)
            {
                Value = CumPV / CumV;
                var v = (CumPV2 / CumV) - (Value * Value);
                Sd = v > 0 ? Math.Sqrt(v) : 0;
            }
        }
        public double Upper(double k = 1.0) => Value + k * Sd;
        public double Lower(double k = 1.0) => Value - k * Sd;
        public double ZScore(double price) => Sd > 0 ? (price - Value) / Sd : 0;
    }
}
