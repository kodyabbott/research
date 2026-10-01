import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.format.ResolverStyle;
import java.util.Locale;

public class Solution {

    private static final DateTimeFormatter[] FORMATS = new DateTimeFormatter[] {
            DateTimeFormatter.ofPattern("uuuu-MM-dd", Locale.ENGLISH)
                    .withResolverStyle(ResolverStyle.STRICT),
            DateTimeFormatter.ofPattern("MM/dd/uuuu", Locale.ENGLISH)
                    .withResolverStyle(ResolverStyle.STRICT),
            DateTimeFormatter.ofPattern("dd-MMM-uuuu", Locale.ENGLISH)
                    .withResolverStyle(ResolverStyle.STRICT),
    };

    public static String toIso(String value) {
        if (value == null) {
            throw new IllegalArgumentException("value must not be null");
        }
        String trimmed = value.trim();
        if (trimmed.isEmpty()) {
            throw new IllegalArgumentException("value must not be blank");
        }
        for (DateTimeFormatter format : FORMATS) {
            try {
                LocalDate parsed = LocalDate.parse(normalizeMonth(trimmed), format);
                return parsed.format(DateTimeFormatter.ISO_LOCAL_DATE);
            } catch (DateTimeParseException ignored) {
                // try the next format
            }
        }
        throw new IllegalArgumentException("unrecognized date: " + value);
    }

    private static String normalizeMonth(String value) {
        int first = value.indexOf('-');
        int second = value.indexOf('-', first + 1);
        if (first != 2 || second != 6) {
            return value;
        }
        String month = value.substring(3, 6);
        return value.substring(0, 3)
                + Character.toUpperCase(month.charAt(0))
                + month.substring(1).toLowerCase(Locale.ENGLISH)
                + value.substring(6);
    }
}
