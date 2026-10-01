import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class Main {
    private static Solution.Player p(String name, int score) {
        return new Solution.Player(name, score);
    }

    public static void main(String[] args) {
        List<Solution.Player> three = Arrays.asList(p("ann", 5), p("bob", 9), p("cy", 7));

        // 1: the Javadoc example.
        Check.eqList(Arrays.asList("bob"),
                Solution.topN(Arrays.asList(p("ann", 5), p("bob", 9)), 1), "javadoc-example");

        // 2: full ordering by score descending.
        Check.eqList(Arrays.asList("bob", "cy", "ann"), Solution.topN(three, 3), "score-desc");

        // 3: n larger than the list returns everything, still ordered.
        Check.eqList(Arrays.asList("bob", "cy", "ann"), Solution.topN(three, 99), "n-too-large");

        // 4-5: n zero and negative.
        Check.eqList(new ArrayList<String>(), Solution.topN(three, 0), "n-zero");
        Check.eqList(new ArrayList<String>(), Solution.topN(three, -2), "n-negative");

        // 6: ties break by name ascending (not shown in the Javadoc).
        Check.eqList(Arrays.asList("abe", "ann", "zed"),
                Solution.topN(Arrays.asList(p("zed", 4), p("ann", 9), p("abe", 9)), 3),
                "ties-by-name-asc");

        // 7: tie-break is stable across a longer run.
        Check.eqList(Arrays.asList("a", "b", "c", "d"),
                Solution.topN(Arrays.asList(p("d", 1), p("c", 1), p("b", 1), p("a", 1)), 4),
                "all-equal-scores-by-name");

        // 8-9: null handling.
        Check.eqList(new ArrayList<String>(), Solution.topN(null, 3), "null-list");
        Check.eqList(Arrays.asList("ann"),
                Solution.topN(Arrays.asList(p("ann", 1), null), 5), "null-element-ignored");

        // 10: negative scores order correctly.
        Check.eqList(Arrays.asList("hi", "lo"),
                Solution.topN(Arrays.asList(p("lo", -9), p("hi", -1)), 2), "negative-scores");

        // 11: empty input.
        Check.eqList(new ArrayList<String>(),
                Solution.topN(new ArrayList<Solution.Player>(), 3), "empty-list");

        Check.report();
    }
}
