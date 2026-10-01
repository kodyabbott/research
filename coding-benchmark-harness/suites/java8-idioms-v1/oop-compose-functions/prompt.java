import java.util.List;
import java.util.function.Function;

public class Solution {

    /**
     * Composes string functions left to right.
     *
     * The returned function applies the list's functions in order: the first function receives the
     * input and each later function receives the previous result. A null or empty list composes to
     * Function.identity(), which returns its input unchanged. Null elements in the list are
     * skipped.
     *
     * Example: [trim, toUpperCase] applied to " ab " gives "AB".
     *
     * @param functions the functions to compose in order, may be null or contain nulls
     * @return the composed function, never null
     */
    public static Function<String, String> composeAll(List<Function<String, String>> functions) {
        throw new UnsupportedOperationException("TODO");
    }
}
