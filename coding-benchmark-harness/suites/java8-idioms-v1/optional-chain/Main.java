public class Main {
    public static void main(String[] args) {
        Solution.Patient full = new Solution.Patient(
                new Solution.Provider(new Solution.Address("84101")));

        // 1: the Javadoc example.
        Check.eqStr("84101", Solution.zipOf(full), "javadoc-example");

        // 2-5: a null at every position (the Javadoc names them; the exact chain is not shown).
        Check.eqStr("UNKNOWN", Solution.zipOf(null), "null-patient");
        Check.eqStr("UNKNOWN", Solution.zipOf(new Solution.Patient(null)), "null-provider");
        Check.eqStr("UNKNOWN", Solution.zipOf(new Solution.Patient(
                new Solution.Provider(null))), "null-address");
        Check.eqStr("UNKNOWN", Solution.zipOf(new Solution.Patient(
                new Solution.Provider(new Solution.Address(null)))), "null-zip");

        // 6-7: blank ZIPs are UNKNOWN too (not shown in the Javadoc example).
        Check.eqStr("UNKNOWN", Solution.zipOf(new Solution.Patient(
                new Solution.Provider(new Solution.Address("")))), "empty-zip");
        Check.eqStr("UNKNOWN", Solution.zipOf(new Solution.Patient(
                new Solution.Provider(new Solution.Address("   ")))), "whitespace-zip");

        // 8: a present ZIP is trimmed.
        Check.eqStr("84101", Solution.zipOf(new Solution.Patient(
                new Solution.Provider(new Solution.Address("  84101  ")))), "zip-is-trimmed");

        // 9: a ZIP+4 is returned as-is once trimmed, not reformatted.
        Check.eqStr("84101-1234", Solution.zipOf(new Solution.Patient(
                new Solution.Provider(new Solution.Address("84101-1234")))), "zip-plus-four");

        // 10: a non-numeric ZIP is still returned; this method does not validate.
        Check.eqStr("ABC", Solution.zipOf(new Solution.Patient(
                new Solution.Provider(new Solution.Address(" ABC ")))), "no-validation");

        Check.report();
    }
}
