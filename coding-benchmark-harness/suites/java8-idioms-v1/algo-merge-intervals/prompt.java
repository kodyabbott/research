import java.util.List;

public class Solution {

    /**
     * Merges overlapping and touching closed intervals.
     *
     * Input intervals are closed ranges given as two-element arrays {start, end} in any order, and
     * may be unsorted. Intervals that overlap, or that merely touch (the end of one equals the
     * start of the next), are merged into one. The result is sorted by start ascending.
     *
     * A null list, an empty list, null elements, and elements that are not length 2 are handled as
     * follows: null list and empty list return an empty list; null elements are ignored; an element
     * whose length is not 2 causes IllegalArgumentException. An interval whose start is greater
     * than its end also causes IllegalArgumentException.
     *
     * Example: [[1,4],[3,6]] returns [[1,6]].
     *
     * @param intervals the intervals to merge, may be null or contain nulls
     * @return merged intervals sorted by start
     * @throws IllegalArgumentException if an element is not length 2 or has start greater than end
     */
    public static List<int[]> merge(List<int[]> intervals) {
        throw new UnsupportedOperationException("TODO");
    }
}
