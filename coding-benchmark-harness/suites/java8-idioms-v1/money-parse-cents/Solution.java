import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class Solution {

    private static final Pattern MONEY = Pattern.compile(
            "^(-?)\\$?(-?)(\\d{1,3}(?:,\\d{3})*|\\d+)(?:\\.(\\d{2}))?$");

    public static long parseCents(String value) {
        if (value == null) {
            throw new IllegalArgumentException("value must not be null");
        }
        String text = value.trim();
        if (text.isEmpty()) {
            throw new IllegalArgumentException("value must not be blank");
        }
        boolean parenthesized = false;
        if (text.startsWith("(") && text.endsWith(")")) {
            parenthesized = true;
            text = text.substring(1, text.length() - 1).trim();
        }
        Matcher matcher = MONEY.matcher(text);
        if (!matcher.matches()) {
            throw new IllegalArgumentException("unrecognized money value: " + value);
        }
        boolean negative = !matcher.group(1).isEmpty() || !matcher.group(2).isEmpty();
        if (negative && parenthesized) {
            throw new IllegalArgumentException("both parentheses and a minus sign: " + value);
        }
        String digits = matcher.group(3).replace(",", "");
        String fraction = matcher.group(4) == null ? "00" : matcher.group(4);
        long cents;
        try {
            cents = Math.addExact(Math.multiplyExact(Long.parseLong(digits), 100L),
                    Long.parseLong(fraction));
        } catch (ArithmeticException overflow) {
            throw new IllegalArgumentException("amount out of range: " + value);
        }
        return (negative || parenthesized) ? -cents : cents;
    }
}
