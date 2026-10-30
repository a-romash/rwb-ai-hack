using System;
using System.IO;
using System.Xml.Linq;

static class Rule {
    public static bool Allowed(int value, int minimum) { return value >= minimum; }
}
class Program {
    static int Main() {
        var suite = new XElement("testsuite");
        var failed = 0;
        foreach (var row in new[] {(4, false), (5, true), (6, true)}) {
            var test = new XElement("testcase", new XAttribute("classname", "AC_01"), new XAttribute("name", "Boundary_"+row.Item1));
            if (Rule.Allowed(row.Item1, 5) != row.Item2) {
                test.Add(new XElement("failure", new XAttribute("type", "AssertionException"), new XAttribute("message", "Assert expected boundary result")));
                failed++;
            }
            suite.Add(test);
        }
        Directory.CreateDirectory("reports");
        new XDocument(suite).Save("reports/junit.xml");
        Console.WriteLine($"AC-01: {3-failed}/3 passed");
        return failed == 0 ? 0 : 1;
    }
}
