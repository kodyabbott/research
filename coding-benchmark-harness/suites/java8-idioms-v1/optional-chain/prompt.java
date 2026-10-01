public class Solution {

    /** DO NOT MODIFY. */
    public static final class Address {
        private final String zip;

        public Address(String zip) {
            this.zip = zip;
        }

        public String getZip() {
            return zip;
        }
    }

    /** DO NOT MODIFY. */
    public static final class Provider {
        private final Address address;

        public Provider(Address address) {
            this.address = address;
        }

        public Address getAddress() {
            return address;
        }
    }

    /** DO NOT MODIFY. */
    public static final class Patient {
        private final Provider provider;

        public Patient(Provider provider) {
            this.provider = provider;
        }

        public Provider getProvider() {
            return provider;
        }
    }

    /**
     * Returns the ZIP code of a patient's provider's address, or "UNKNOWN".
     *
     * "UNKNOWN" is returned when the patient is null, the provider is null, the address is null,
     * the ZIP is null, or the ZIP is blank once trimmed. Otherwise the trimmed ZIP is returned.
     *
     * Example: a patient whose provider's address has ZIP "84101" returns "84101".
     *
     * @param patient the patient, may be null with nulls at any level
     * @return the trimmed ZIP, or "UNKNOWN"
     */
    public static String zipOf(Patient patient) {
        throw new UnsupportedOperationException("TODO");
    }
}
