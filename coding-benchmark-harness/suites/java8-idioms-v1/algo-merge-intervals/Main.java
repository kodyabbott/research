import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class Main {
    private static List<int[]> input(int[]... intervals) {
        return Arrays.asList(intervals);
    }

    private static int[] iv(int start, int end) {
        return new int[] {start, end};
    }

    /** Compares as a nested array so Check.eq's deepEquals sees the int[] contents. */
    private static void same(int[][] expected, List<int[]> actual, String name) {
        Check.eq(expected, actual == null ? null : actual.toArray(new int[0][]), name);
    }

    public static void main(String[] args) {
        // 1: the Javadoc example.
        same(new int[][] {iv(1, 6)}, Solution.merge(input(iv(1, 4), iv(3, 6))), "javadoc-example");

        // 2-3: empty and null.
        same(new int[][] {}, Solution.merge(new ArrayList<int[]>()), "empty-list");
        same(new int[][] {}, Solution.merge(null), "null-list");

        // 4: a single interval passes through.
        same(new int[][] {iv(2, 5)}, Solution.merge(input(iv(2, 5))), "single");

        // 5: unsorted input is sorted (not shown in the Javadoc).
        same(new int[][] {iv(1, 6), iv(7, 9), iv(15, 15)},
                Solution.merge(input(iv(7, 9), iv(1, 4), iv(3, 6), iv(15, 15))), "unsorted-input");

        // 6: touching intervals merge (end of one equals start of the next).
        same(new int[][] {iv(1, 5)}, Solution.merge(input(iv(1, 3), iv(3, 5))), "touching-merge");

        // 7: a gap of one keeps them separate.
        same(new int[][] {iv(1, 3), iv(4, 5)}, Solution.merge(input(iv(1, 3), iv(4, 5))),
                "adjacent-but-not-touching");

        // 8: a fully contained interval does not shrink the outer one.
        same(new int[][] {iv(1, 10)}, Solution.merge(input(iv(1, 10), iv(3, 4))), "contained");

        // 9: a degenerate point interval.
        same(new int[][] {iv(5, 5)}, Solution.merge(input(iv(5, 5))), "point-interval");

        // 10: a point interval touching a range merges.
        same(new int[][] {iv(1, 3)}, Solution.merge(input(iv(1, 3), iv(3, 3))), "point-touching");

        // 11: null elements are ignored.
        same(new int[][] {iv(1, 2)}, Solution.merge(Arrays.asList(null, iv(1, 2), null)),
                "null-elements-ignored");

        // 12: negative bounds.
        same(new int[][] {iv(-5, -1), iv(0, 2)},
                Solution.merge(input(iv(0, 2), iv(-5, -3), iv(-4, -1))), "negative-bounds");

        // 13: three that chain into one.
        same(new int[][] {iv(1, 9)},
                Solution.merge(input(iv(1, 3), iv(2, 6), iv(5, 9))), "chained-merge");

        // 14: the input list is not mutated.
        int[] shared = iv(3, 6);
        List<int[]> given = input(iv(1, 4), shared);
        Solution.merge(given);
        Check.eq(iv(3, 6), shared, "input-not-mutated");

        // 15-16: rejections.
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.merge(input(new int[] {1, 2, 3})), "wrong-length-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.merge(input(iv(5, 1))), "start-after-end-throws");

        Check.report();
    }
}
