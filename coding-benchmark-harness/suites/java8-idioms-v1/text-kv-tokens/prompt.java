import java.util.LinkedHashMap;

public class Solution {

    /**
     * Parses a semicolon-separated key=value string.
     *
     * Pairs are separated by ";" and a pair is split on its first "=" only, so a value may itself
     * contain "=". Keys and values are percent-decoded: "%XX" becomes the byte XX interpreted as
     * UTF-8, and "+" is left as a literal plus. Empty values are allowed; empty keys are not.
     * When a key repeats, the last occurrence wins, but the key keeps its first-seen position.
     * Empty segments (for example a trailing ";") are skipped. A null or blank input gives an
     * empty map. Iteration order is first-seen key order.
     *
     * Example: "a=1;b=2" returns {a=1, b=2}.
     *
     * @param input the encoded pairs
     * @return the decoded pairs in first-seen key order
     * @throws IllegalArgumentException if a segment has no "=", has an empty key, or contains a
     *                                  malformed percent escape
     */
    public static LinkedHashMap<String, String> parse(String input) {
        throw new UnsupportedOperationException("TODO");
    }
}
