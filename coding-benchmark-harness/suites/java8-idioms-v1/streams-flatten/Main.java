import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class Main {
    public static void main(String[] args) {
        // 1: the Javadoc example.
        Check.eqList(Arrays.asList("a", "b"), Solution.flatten(Arrays.asList(
                Arrays.asList("b", " a "), Arrays.asList("A", ""))), "javadoc-example");

        // 2: nested empties and a null inner list.
        Check.eqList(new ArrayList<String>(), Solution.flatten(Arrays.asList(
                new ArrayList<String>(), null, new ArrayList<String>())), "nested-empties");

        // 3: null outer list.
        Check.eqList(new ArrayList<String>(), Solution.flatten(null), "null-outer");

        // 4: first occurrence wins for case variants (not in the Javadoc examples).
        Check.eqList(Arrays.asList("Bee"), Solution.flatten(Arrays.asList(
                Arrays.asList("Bee", "bee", "BEE"))), "first-case-variant-kept");

        // 5: blank-only values are dropped.
        Check.eqList(Arrays.asList("x"), Solution.flatten(Arrays.asList(
                Arrays.asList("   ", "\t", "x", ""))), "blank-values-dropped");

        // 6: nulls inside an inner list.
        Check.eqList(Arrays.asList("keep"), Solution.flatten(Arrays.asList(
                Arrays.asList(null, "keep", null))), "null-values-dropped");

        // 7: case-insensitive sort order, not natural order (natural would put "Zeta" first).
        Check.eqList(Arrays.asList("alpha", "Beta", "Zeta"), Solution.flatten(Arrays.asList(
                Arrays.asList("Zeta", "alpha", "Beta"))), "case-insensitive-sort");

        // 8: trimming happens before de-duplication.
        Check.eqList(Arrays.asList("dup"), Solution.flatten(Arrays.asList(
                Arrays.asList("  dup", "dup  ", " DUP "))), "trim-then-dedupe");

        // 9: values from several inner lists interleave correctly.
        Check.eqList(Arrays.asList("a", "b", "c", "d"), Solution.flatten(Arrays.asList(
                Arrays.asList("d", "b"), Arrays.asList("c"), Arrays.asList("a", "B"))),
                "across-inner-lists");

        Check.report();
    }
}
