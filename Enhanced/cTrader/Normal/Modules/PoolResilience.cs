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
            Resilience = consumed > 0 ? refilled / consumed : 0;
            Exploitable = Density > 0.5 && Depth > 0 && Resilience < 0.30;
        }
    }
}
