public class Main {
    public static void main(String[] args) {
        // 1-3: the three documented formats.
        Check.eqStr("2026-03-08", Solution.toIso("2026-03-08"), "iso-passthrough");
        Check.eqStr("2026-03-08", Solution.toIso("03/08/2026"), "us-slash");
        Check.eqStr("2026-03-08", Solution.toIso("08-Mar-2026"), "dd-mmm-yyyy");

        // 4: surrounding whitespace.
        Check.eqStr("2026-12-31", Solution.toIso("  12/31/2026  "), "whitespace-trimmed");

        // 5-6: month name case-insensitivity (documented, but these spellings are not shown).
        Check.eqStr("2026-01-09", Solution.toIso("09-JAN-2026"), "month-upper");
        Check.eqStr("2026-11-02", Solution.toIso("02-nov-2026"), "month-lower");

        // 7: single-digit day and month must still be zero-padded on input.
        Check.eqStr("2026-07-04", Solution.toIso("07/04/2026"), "padded-us");

        // 8: a leap day in a leap year is valid.
        Check.eqStr("2028-02-29", Solution.toIso("29-Feb-2028"), "valid-leap-day");

        // 9: a non-existent leap day is rejected, not rolled over (not in the Javadoc examples).
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.toIso("2026-02-30"), "non-existent-date-throws");

        // 10: February 30 in slash form is rejected too.
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.toIso("02/30/2026"), "non-existent-slash-throws");

        // 11-13: null, blank and unrecognized.
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.toIso(null), "null-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.toIso("   "), "blank-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.toIso("March 8, 2026"), "unrecognized-format-throws");

        // 14: a month name that is not English is rejected.
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.toIso("08-Mrz-2026"), "non-english-month-throws");

        Check.report();
    }
}
