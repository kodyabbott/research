import java.util.Optional;

public class Solution {

    public static final class Address {
        private final String zip;

        public Address(String zip) {
            this.zip = zip;
        }

        public String getZip() {
            return zip;
        }
    }

    public static final class Provider {
        private final Address address;

        public Provider(Address address) {
            this.address = address;
        }

        public Address getAddress() {
            return address;
        }
    }

    public static final class Patient {
        private final Provider provider;

        public Patient(Provider provider) {
            this.provider = provider;
        }

        public Provider getProvider() {
            return provider;
        }
    }

    public static String zipOf(Patient patient) {
        return Optional.ofNullable(patient)
                .map(Patient::getProvider)
                .map(Provider::getAddress)
                .map(Address::getZip)
                .map(String::trim)
                .filter(zip -> !zip.isEmpty())
                .orElse("UNKNOWN");
    }
}
