namespace GodmodeOfea.Enhanced
{
    public class SweepResult
    {
        public bool Fired;
        public int Direction;
        public int PreconditionsPassed;
        public double SweepExtreme;
        public double AbsorptionScore;
    }

    public class SweepDetector
    {
        public SweepResult Last = new SweepResult();
        public void Evaluate(bool eq, bool htf, bool kz, bool mom, bool abs_, bool flip,
                             int dir, double extreme, double absScore = 0)
        {
            int n = 0;
            if (eq) n++; if (htf) n++; if (kz) n++; if (mom) n++; if (abs_) n++; if (flip) n++;
            Last = new SweepResult
            {
                PreconditionsPassed = n,
                Fired = n == 6,
                Direction = dir,
                SweepExtreme = extreme,
                AbsorptionScore = absScore
            };
        }
        public double ExpectedR()
        {
            switch (Last.PreconditionsPassed) { case 6: return 1.18; case 5: return 0.94; case 4: return 0.55; case 3: return 0.31; default: return 0.08; }
        }
        public double EmpiricalWinRate()
        {
            switch (Last.PreconditionsPassed) { case 6: return 0.67; case 5: return 0.63; case 4: return 0.58; case 3: return 0.54; default: return 0.49; }
        }
    }
}
