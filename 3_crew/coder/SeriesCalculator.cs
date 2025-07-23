using System;

public class SeriesCalculator
{
    public static void Main(string[] args)
    {
        double sum = 0.0;
        for (int i = 0; i < 1000; i++)
        {
            sum += Math.Pow(-1, i) / (2 * i + 1);
        }
        sum *= 3;

        Console.WriteLine(sum);
    }
}
