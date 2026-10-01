public class Solution {

    /**
     * Normalizes a date written in one of three formats to ISO-8601 (yyyy-MM-dd).
     *
     * Accepted inputs, tried in this order:
     *   yyyy-MM-dd   e.g. "2026-03-08"
     *   MM/dd/yyyy   e.g. "03/08/2026"
     *   dd-MMM-yyyy  e.g. "08-Mar-2026", with the English three-letter month, case-insensitive
     *
     * Surrounding whitespace is ignored. The returned string is always yyyy-MM-dd.
     *
     * @param value the date to normalize
     * @return the same date as yyyy-MM-dd
     * @throws IllegalArgumentException if value is null, blank, or not one of the three formats,
     *                                  including a syntactically valid but non-existent date
     */
    public static String toIso(String value) {
        throw new UnsupportedOperationException("TODO");
    }
}
