import java.util.ArrayList;
import java.util.Arrays;

public class Main {
    public static void main(String[] args) {
        // 1: the Javadoc example.
        Check.eqList(Arrays.asList("the"), Solution.topWords("the cat the", 1), "javadoc-example");

        // 2: ordering by frequency.
        Check.eqList(Arrays.asList("the", "cat"), Solution.topWords("the cat the", 2),
                "frequency-order");

        // 3: ties break by word ascending (not shown in the Javadoc).
        Check.eqList(Arrays.asList("apple", "banana", "cherry"),
                Solution.topWords("cherry banana apple", 3), "ties-by-word-asc");

        // 4: k larger than the number of distinct words.
        Check.eqList(Arrays.asList("a", "b"), Solution.topWords("b a a b", 99), "k-too-large");

        // 5-6: k zero and negative.
        Check.eqList(new ArrayList<String>(), Solution.topWords("a b", 0), "k-zero");
        Check.eqList(new ArrayList<String>(), Solution.topWords("a b", -1), "k-negative");

        // 7-8: null and word-free text.
        Check.eqList(new ArrayList<String>(), Solution.topWords(null, 3), "null-text");
        Check.eqList(new ArrayList<String>(), Solution.topWords("!!! ,.-", 3), "no-words");

        // 9: punctuation splits words and is stripped.
        Check.eqList(Arrays.asList("cat", "dog"), Solution.topWords("cat, dog. cat-dog", 2),
                "punctuation-splits");

        // 10: case folding, and the result is lower-cased.
        Check.eqList(Arrays.asList("cat"), Solution.topWords("Cat CAT cAt", 1), "case-folded");

        // 11: digits count as word characters.
        Check.eqList(Arrays.asList("abc123"), Solution.topWords("abc123 abc123", 1),
                "digits-in-words");

        // 12: a mixed case tie is compared on the lower-cased form.
        Check.eqList(Arrays.asList("alpha", "beta"), Solution.topWords("Beta ALPHA", 2),
                "tie-on-lowercased-form");

        // 13: frequency beats alphabetical order.
        Check.eqList(Arrays.asList("zzz", "aaa"), Solution.topWords("zzz aaa zzz", 2),
                "frequency-beats-alphabet");

        Check.report();
    }
}
