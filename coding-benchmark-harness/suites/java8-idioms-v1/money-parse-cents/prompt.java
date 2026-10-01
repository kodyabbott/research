public class Solution {

    /**
     * Parses a money string into whole cents.
     *
     * Accepted forms, after trimming surrounding whitespace:
     *   an optional leading "$"
     *   an optional leading "-" for a negative amount, before or after the "$"
     *   grouping commas between digit groups, for example "1,234.56"
     *   exactly zero or two decimal places
     *   parentheses around the whole amount to mean negative, for example "(12.30)" is -1230
     *
     * Examples: "$1,234.56" is 123456; "(12.30)" is -1230; "-0.01" is -1; "45" is 4500.
     *
     * @param value the money string
     * @return the amount in whole cents
     * @throws IllegalArgumentException if value is null, blank, or not one of the accepted forms
     */
    public static long parseCents(String value) {
        throw new UnsupportedOperationException("TODO");
    }
}
