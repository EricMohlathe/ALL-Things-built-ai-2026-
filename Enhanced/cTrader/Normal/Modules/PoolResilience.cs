namespace GodmodeOfea.Enhanced
{
    public class PoolResilience
    {
        public double Density, Depth, Resilience;
        public bool Exploitable;
        public void Compute(double consumed, double refilled, double levelSize, int orderCount, int tickRange)
        {
            Depth = levelSize;
            Density = tickRange > 0 ? (double)orderCount / (double)tickRange : 0;
            // Only emit a resilience reading when there's actual consumption to
            // measure against. The previous version produced Resilience=0 when
            // consumed==0, which then falsely satisfied the < 0.30 exploitability
            // check on quiet markets.
            bool hasFlow = consumed > 0;
            Resilience = hasFlow ? refilled / consumed : 0;
            Exploitable = hasFlow && Density > 0.5 && Depth > 0 && Resilience < 0.30;
        }
    }
}
