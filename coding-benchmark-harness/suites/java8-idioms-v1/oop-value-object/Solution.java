import java.util.ArrayList;
import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.TreeSet;

public class Solution {

    public static final class Mrn implements Comparable<Mrn> {
        private final String raw;

        public Mrn(String raw) {
            if (raw == null) {
                throw new IllegalArgumentException("raw must not be null");
            }
            this.raw = raw;
        }

        public String raw() {
            return raw;
        }

        public String normalized() {
            return raw.trim().toUpperCase(Locale.ROOT);
        }

        @Override
        public boolean equals(Object other) {
            if (this == other) {
                return true;
            }
            if (!(other instanceof Mrn)) {
                return false;
            }
            return normalized().equals(((Mrn) other).normalized());
        }

        @Override
        public int hashCode() {
            return normalized().hashCode();
        }

        @Override
        public int compareTo(Mrn other) {
            return normalized().compareTo(other.normalized());
        }

        @Override
        public String toString() {
            return normalized();
        }
    }

    public static int countDistinct(Collection<Mrn> values) {
        if (values == null) {
            return 0;
        }
        Set<Mrn> seen = new HashSet<Mrn>();
        for (Mrn value : values) {
            if (value != null) {
                seen.add(value);
            }
        }
        return seen.size();
    }

    public static List<String> sortedDistinct(Collection<Mrn> values) {
        List<String> out = new ArrayList<String>();
        if (values == null) {
            return out;
        }
        Set<Mrn> sorted = new TreeSet<Mrn>();
        for (Mrn value : values) {
            if (value != null) {
                sorted.add(value);
            }
        }
        for (Mrn value : sorted) {
            out.add(value.normalized());
        }
        return out;
    }
}
