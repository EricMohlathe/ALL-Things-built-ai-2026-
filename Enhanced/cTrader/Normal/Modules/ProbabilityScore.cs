namespace GodmodeOfea.Enhanced
{
    public class ProbabilityWeights
    {
        public double F1 = 12, F2 = 8, F3 = 12, F4 = 10, F5 = 8;
        public double F6 = 8, F7 = 12, F8 = 6, F9 = 8, F10 = 6, F11 = 4, F12 = 6;
    }

    public class ProbabilityScore
    {
        public ProbabilityWeights W = new ProbabilityWeights();
        public double Total;

        private static double C(double x) => x < 0 ? 0 : (x > 1 ? 1 : x);

        public double Compute(double g1, double g2, double g3, double g4, double g5,
                              double g6, double g7, double g8, double g9, double g10,
                              double g11, double g12)
        {
            Total = W.F1 * C(g1) + W.F2 * C(g2) + W.F3 * C(g3) + W.F4 * C(g4) + W.F5 * C(g5)
                  + W.F6 * C(g6) + W.F7 * C(g7) + W.F8 * C(g8) + W.F9 * C(g9) + W.F10 * C(g10)
                  + W.F11 * C(g11) + W.F12 * C(g12);
            return Total;
        }
        public string Grade()
        {
            if (Total >= 85) return "A+";
            if (Total >= 75) return "A";
            if (Total >= 65) return "B";
            if (Total >= 50) return "C";
            if (Total >= 35) return "D";
            return "F";
        }
    }
}
