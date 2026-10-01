import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

public class Solution {

    public static List<int[]> merge(List<int[]> intervals) {
        List<int[]> out = new ArrayList<int[]>();
        if (intervals == null) {
            return out;
        }
        List<int[]> valid = new ArrayList<int[]>();
        for (int[] interval : intervals) {
            if (interval == null) {
                continue;
            }
            if (interval.length != 2) {
                throw new IllegalArgumentException("interval must have length 2");
            }
            if (interval[0] > interval[1]) {
                throw new IllegalArgumentException(
                        "start must not exceed end: " + interval[0] + " > " + interval[1]);
            }
            valid.add(new int[] {interval[0], interval[1]});
        }
        if (valid.isEmpty()) {
            return out;
        }
        valid.sort(Comparator.<int[]>comparingInt(a -> a[0]).thenComparingInt(a -> a[1]));
        int[] current = new int[] {valid.get(0)[0], valid.get(0)[1]};
        for (int i = 1; i < valid.size(); i++) {
            int[] next = valid.get(i);
            if (next[0] <= current[1]) {
                current[1] = Math.max(current[1], next[1]);
            } else {
                out.add(current);
                current = new int[] {next[0], next[1]};
            }
        }
        out.add(current);
        return out;
    }
}
