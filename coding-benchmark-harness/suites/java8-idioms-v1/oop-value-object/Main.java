import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Hidden tests for oop-value-object. Literal expectations only; never calls Solution to
 *  compute an expected value. */
public class Main {
    public static void main(String[] args) {
        Solution.Mrn a1 = new Solution.Mrn("a1");
        Solution.Mrn a1Padded = new Solution.Mrn("  A1  ");
        Solution.Mrn b2 = new Solution.Mrn("b2");

        // 1-2: normalization and raw preservation (shown in the Javadoc).
        Check.eqStr("A1", a1.normalized(), "normalized-upper");
        Check.eqStr("  A1  ", a1Padded.raw(), "raw-unchanged");

        // 3-5: equality contract (null and other-type cases are NOT in the Javadoc examples).
        Check.eqBool(true, a1.equals(a1Padded), "equals-ignores-case-and-padding");
        Check.eqBool(true, a1Padded.equals(a1), "equals-symmetric");
        Check.eqBool(true, a1.equals(a1), "equals-reflexive");
        Check.eqBool(false, a1.equals(null), "equals-null-is-false");
        Check.eqBool(false, a1.equals("A1"), "equals-other-type-is-false");
        Check.eqBool(false, a1.equals(b2), "equals-different-value");

        // 6-7: hashCode consistency.
        Check.eqBool(true, a1.hashCode() == a1Padded.hashCode(), "hashcode-consistent-with-equals");
        Check.eqInt("A1".hashCode(), a1.hashCode(), "hashcode-of-normalized-value");

        // 8-10: compareTo, consistent with equals.
        Check.eqInt(0, a1.compareTo(a1Padded), "compareto-equal-is-zero");
        Check.eqBool(true, a1.compareTo(b2) < 0, "compareto-ascending");
        Check.eqBool(true, b2.compareTo(a1) > 0, "compareto-reversed");

        // 11-13: countDistinct, including inputs not shown in the Javadoc.
        Check.eqInt(2, Solution.countDistinct(Arrays.asList(a1, a1Padded, b2)), "distinct-javadoc");
        Check.eqInt(0, Solution.countDistinct(new ArrayList<Solution.Mrn>()), "distinct-empty");
        Check.eqInt(0, Solution.countDistinct(null), "distinct-null-collection");
        Check.eqInt(1, Solution.countDistinct(Arrays.asList(a1, null, a1Padded)),
                "distinct-ignores-nulls");
        Check.eqInt(3, Solution.countDistinct(Arrays.asList(
                new Solution.Mrn("z9"), new Solution.Mrn("Z8"), new Solution.Mrn(" z7 "))),
                "distinct-three-unshown");

        // 14-17: sortedDistinct.
        Check.eqList(Arrays.asList("A1", "B2"),
                Solution.sortedDistinct(Arrays.asList(b2, a1, a1Padded)), "sorted-javadoc");
        Check.eqList(new ArrayList<String>(), Solution.sortedDistinct(null), "sorted-null");
        Check.eqList(new ArrayList<String>(), Solution.sortedDistinct(
                new ArrayList<Solution.Mrn>()), "sorted-empty");
        Check.eqList(Arrays.asList("MRN-1", "MRN-10", "MRN-2"),
                Solution.sortedDistinct(Arrays.asList(new Solution.Mrn("mrn-2"),
                        new Solution.Mrn("MRN-10"), new Solution.Mrn(" mrn-1 "))),
                "sorted-lexical-not-numeric");

        // 18: the constructor contract.
        Check.throwsType(IllegalArgumentException.class, new Check.ThrowingRunnable() {
            public void run() {
                new Solution.Mrn(null);
            }
        }, "constructor-rejects-null");

        Check.report();
    }
}
