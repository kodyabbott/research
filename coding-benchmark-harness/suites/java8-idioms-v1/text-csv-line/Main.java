import java.util.Arrays;

public class Main {
    public static void main(String[] args) {
        // 1: the Javadoc example.
        Check.eqList(Arrays.asList("a", "b,c", "d\"e"),
                Solution.parseLine("a,\"b,c\",\"d\"\"e\""), "javadoc-example");

        // 2-3: plain fields and a single field.
        Check.eqList(Arrays.asList("a", "b", "c"), Solution.parseLine("a,b,c"), "plain-fields");
        Check.eqList(Arrays.asList("only"), Solution.parseLine("only"), "single-field");

        // 4-6: empty fields (not shown in the Javadoc).
        Check.eqList(Arrays.asList(""), Solution.parseLine(""), "empty-input");
        Check.eqList(Arrays.asList("a", ""), Solution.parseLine("a,"), "trailing-empty-field");
        Check.eqList(Arrays.asList("", "a"), Solution.parseLine(",a"), "leading-empty-field");
        Check.eqList(Arrays.asList("a", "", "b"), Solution.parseLine("a,,b"), "middle-empty-field");

        // 7: whitespace is preserved exactly.
        Check.eqList(Arrays.asList(" a ", "b "), Solution.parseLine(" a ,b "), "whitespace-kept");

        // 8: a quoted empty field.
        Check.eqList(Arrays.asList("", "x"), Solution.parseLine("\"\",x"), "quoted-empty");

        // 9: a quote that is not at the start of a field is literal.
        Check.eqList(Arrays.asList("a\"b"), Solution.parseLine("a\"b"), "quote-mid-field-literal");

        // 10: a field that is only a doubled quote.
        Check.eqList(Arrays.asList("\""), Solution.parseLine("\"\"\"\""), "single-escaped-quote");

        // 11: a quoted field containing only a comma.
        Check.eqList(Arrays.asList(","), Solution.parseLine("\",\""), "quoted-comma-only");

        // 12: quoted field followed by more fields.
        Check.eqList(Arrays.asList("a,b", "c", ""), Solution.parseLine("\"a,b\",c,"),
                "quoted-then-trailing-empty");

        // 13-15: rejections.
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.parseLine(null), "null-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.parseLine("\"unterminated"), "unterminated-quote-throws");
        Check.throwsType(IllegalArgumentException.class,
                () -> Solution.parseLine("\"a\"b"), "text-after-quote-throws");

        Check.report();
    }
}
